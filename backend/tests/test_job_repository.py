"""
The job store, against a real Postgres.

These skip unless `TEST_DATABASE_URL` points at a live PostGIS database, because
the schema is Postgres-specific — `geography(Point,4326)`, a partial unique
index, `uuid` primary keys — and a SQLite stand-in would prove that a different
schema works.

    docker compose up -d
    createdb -h localhost -p 5433 -U realestate realestate_test   # once
    TEST_DATABASE_URL=postgresql+asyncpg://realestate:realestate@localhost:5433/realestate_test \\
      make test-db
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.job import Job
from app.repositories import jobRepository
from app.repositories.jobRepository import TerminalJobError

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.skipif(
        not TEST_DATABASE_URL,
        reason="TEST_DATABASE_URL is not set — needs a live PostGIS (docker compose up -d)",
    ),
    pytest.mark.asyncio,
]


@pytest_asyncio.fixture
async def db():
    """
    A session on a schema built by the migrations, not by `create_all`.

    Running Alembic here is deliberate: it means these tests also prove
    `alembic upgrade head` succeeds on an empty database, which is S2's first
    exit proof.
    """
    from alembic.config import Config

    from alembic import command

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")

    engine = create_async_engine(TEST_DATABASE_URL)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


async def test_a_created_job_is_queued_and_not_terminal(db):
    job = await jobRepository.create(db, job_type="valuation_report", instructions="value it")
    assert job.status == "queued"
    assert job.terminal_at is None
    assert job.is_terminal is False


async def test_status_moves_and_terminal_at_is_stamped_on_completion(db):
    job = await jobRepository.create(db, job_type="rent_roll_report")

    await jobRepository.set_status(db, job.id, "processing")
    assert (await jobRepository.get(db, job.id)).terminal_at is None

    await jobRepository.set_status(db, job.id, "completed", doc_url="s3://x/y.docx")
    done = await jobRepository.get(db, job.id)
    assert done.status == "completed"
    assert done.doc_url == "s3://x/y.docx"
    assert done.terminal_at is not None


async def test_a_terminal_job_refuses_any_further_status_write(db):
    """
    The guard the sprint plan asks for, and the reason it is at the repository
    layer: from S4 there are several writers, and a rule enforced in one caller
    is a rule the next caller does not know about.
    """
    job = await jobRepository.create(db)
    await jobRepository.set_status(db, job.id, "completed", doc_url="s3://x/y.docx")

    for attempted in ("failed", "processing", "queued", "completed"):
        with pytest.raises(TerminalJobError) as excinfo:
            await jobRepository.set_status(db, job.id, attempted, error="late write")
        assert str(job.id) in str(excinfo.value)
        assert attempted in str(excinfo.value)

    unchanged = await jobRepository.get(db, job.id)
    assert unchanged.status == "completed"
    assert unchanged.doc_url == "s3://x/y.docx"
    assert unchanged.error == ""


async def test_a_failed_job_is_equally_final(db):
    job = await jobRepository.create(db)
    await jobRepository.set_status(db, job.id, "failed", error="no comparables")

    with pytest.raises(TerminalJobError):
        await jobRepository.set_status(db, job.id, "completed", doc_url="s3://sneaky.docx")

    assert (await jobRepository.get(db, job.id)).status == "failed"


async def test_a_job_interrupted_mid_graph_survives_and_is_reconcilable(db):
    """
    S1 lost this job entirely: `jobs.json` was rewritten from memory on restart.
    Now the row is still there, still `processing`, and countable — which is what
    makes it something S4's sweep can act on rather than something nobody knows
    happened.
    """
    job = await jobRepository.create(db, job_type="valuation_report")
    await jobRepository.set_status(db, job.id, "processing")

    # Simulate the restart: a brand new engine, session and connection pool.
    engine = create_async_engine(TEST_DATABASE_URL)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as fresh:
        survivor = await jobRepository.get(fresh, job.id)
        assert survivor is not None
        assert survivor.status == "processing"
        assert survivor.terminal_at is None

        orphans = await jobRepository.reconcile_orphans(
            fresh, older_than=datetime.now(UTC) + timedelta(seconds=1)
        )
        assert orphans == 1
    await engine.dispose()


async def test_an_unknown_job_id_is_a_lookup_error_not_a_silent_no_op(db):
    with pytest.raises(LookupError):
        await jobRepository.set_status(db, uuid.uuid4(), "completed")


async def test_the_idempotency_index_is_partial(db):
    """
    Two jobs may both have no key; two jobs may not share one. Without the
    partial predicate the second unkeyed job would collide (S4 depends on this).
    """
    await jobRepository.create(db, idempotency_key=None)
    await jobRepository.create(db, idempotency_key=None)

    key = "a" * 64
    await jobRepository.create(db, idempotency_key=key)
    with pytest.raises(IntegrityError):
        await jobRepository.create(db, idempotency_key=key)


async def test_the_gist_index_on_properties_geom_exists(db):
    """
    S2's exit proof, asked of the database rather than of the migration file.
    Autogenerate does not emit this index; without it comparable search degrades
    to a sequential scan, silently.
    """
    from sqlalchemy import text

    rows = (
        await db.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE tablename = 'properties' AND indexname = 'ix_properties_geom'"
            )
        )
    ).scalars().all()

    assert rows, "ix_properties_geom is missing"
    assert "gist" in rows[0].lower(), rows[0]


async def test_postgis_is_enabled(db):
    from sqlalchemy import text

    version = (await db.execute(text("SELECT postgis_version()"))).scalar_one()
    assert version


async def test_a_job_row_carries_no_monetary_float(db):
    from sqlalchemy import text

    rows = (
        await db.execute(
            text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name IN ('jobs','properties')"
            )
        )
    ).all()
    floats = [r for r in rows if r.data_type in ("real", "double precision")]
    assert floats == [], f"float columns found: {floats}"


async def test_job_model_exposes_is_terminal(db):
    job = Job(status="queued")
    assert job.is_terminal is False
