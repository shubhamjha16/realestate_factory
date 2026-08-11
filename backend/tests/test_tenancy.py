"""
S5's exit proof: firm A cannot reach firm B's data by any route.

The plan asks for four attempts — read, list, search and download — all denied,
and answered 404 rather than 403. Each is exercised here at the repository layer,
which is where tenancy is enforced, and again over HTTP, which is where a caller
would actually try it.

Needs a live PostGIS. Skips otherwise, and runs in CI's `database` job.
"""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.firm import Firm
from app.repositories import (
    clientRepository,
    jobRepository,
    mandateRepository,
    propertyRepository,
    userRepository,
)
from app.services.access.authz import require_edit, require_sign
from app.services.access.scope import FirmScope
from app.services.authService import scope_for

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.skipif(
        not TEST_DATABASE_URL,
        reason="TEST_DATABASE_URL is not set — needs a live PostGIS (docker compose up -d)",
    ),
    pytest.mark.asyncio,
]


def _rebuild_schema() -> None:
    from alembic.config import Config

    from alembic import command

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


@pytest_asyncio.fixture
async def db():
    await asyncio.to_thread(_rebuild_schema)
    engine = create_async_engine(TEST_DATABASE_URL)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


async def _firm_with_data(db, name: str) -> tuple[FirmScope, dict]:
    firm = Firm(name=name)
    db.add(firm)
    await db.flush()

    user = await userRepository.create(
        db, firm_id=firm.id, email=f"partner@{name.lower()}.test", role="partner"
    )
    scope = scope_for(user)

    client = await clientRepository.create(db, scope, name=f"{name} Bank", kind="bank")
    mandate = await mandateRepository.create(
        db, scope, client_id=client.id, kind="valuation", purpose="loan"
    )
    prop = await propertyRepository.create(
        db, scope, title=f"{name} Tower", mandate_id=mandate.id, city="Pune"
    )
    job = await jobRepository.create(
        db, scope, job_type="valuation_report", instructions=f"{name} secret instruction"
    )
    return scope, {"client": client, "mandate": mandate, "property": prop, "job": job}


@pytest_asyncio.fixture
async def two_firms(db):
    a_scope, a = await _firm_with_data(db, "Alpha")
    b_scope, b = await _firm_with_data(db, "Bravo")
    return (a_scope, a), (b_scope, b)


# ── the four attempted paths ──────────────────────────────────────────────────


async def test_firm_a_cannot_read_firm_b(db, two_firms):
    (a_scope, _), (_, b) = two_firms

    assert await jobRepository.get(db, a_scope, b["job"].id) is None
    assert await mandateRepository.get(db, a_scope, b["mandate"].id) is None
    assert await propertyRepository.get(db, a_scope, b["property"].id) is None
    assert await clientRepository.get(db, a_scope, b["client"].id) is None
    assert await userRepository.get(db, a_scope, b["mandate"].firm_id) is None


async def test_firm_a_cannot_list_firm_b(db, two_firms):
    (a_scope, a), (_, b) = two_firms

    job_ids = {j.id for j in await jobRepository.list_jobs(db, a_scope)}
    assert a["job"].id in job_ids
    assert b["job"].id not in job_ids

    assert {m.id for m in await mandateRepository.list_mandates(db, a_scope)} == {a["mandate"].id}
    assert {p.id for p in await propertyRepository.list_properties(db, a_scope)} == {a["property"].id}
    assert {c.id for c in await clientRepository.list_clients(db, a_scope)} == {a["client"].id}


async def test_firm_a_cannot_search_firm_b(db, two_firms):
    """
    The one most often missed: the listing gets scoped and the search beside it
    does not.
    """
    (a_scope, _), (_, b) = two_firms

    assert await jobRepository.search(db, a_scope, "Bravo secret") == []
    assert await propertyRepository.search(db, a_scope, "Bravo") == []
    assert await clientRepository.search(db, a_scope, "Bravo") == []

    # ...and the search still works for its own firm, so this is not passing
    # because search is broken.
    assert len(await jobRepository.search(db, a_scope, "Alpha secret")) == 1


async def test_firm_a_cannot_reach_firm_b_by_spatial_search(db, two_firms):
    """Comparable search is a query too, and it leaks location if unscoped."""
    (a_scope, _), (b_scope, b) = two_firms

    b["property"].geom = "SRID=4326;POINT(73.8567 18.5204)"
    db.add(b["property"])
    await db.commit()

    nearby = await propertyRepository.search_nearby(
        db, a_scope, lat=18.5204, lng=73.8567, radius_m=50_000
    )
    assert nearby == []

    assert len(
        await propertyRepository.search_nearby(
            db, b_scope, lat=18.5204, lng=73.8567, radius_m=50_000
        )
    ) == 1


async def test_firm_a_cannot_download_firm_b(db, two_firms):
    """
    Download is a read of the job that holds the URL. Denying the read denies the
    download; there is no separate path to the document.
    """
    (a_scope, _), (b_scope, b) = two_firms
    await jobRepository.set_status(db, b["job"].id, "completed", doc_url="s3://bravo/report.docx")

    assert await jobRepository.get(db, a_scope, b["job"].id) is None
    visible = await jobRepository.get(db, b_scope, b["job"].id)
    assert visible is not None and visible.doc_url == "s3://bravo/report.docx"


# ── denials are 404, over HTTP ────────────────────────────────────────────────


async def test_a_cross_firm_read_is_404_over_http_not_403(db, two_firms):
    """
    403 says "this exists, but not for you". For a mandate name or a property
    address that confirmation is the leak.
    """
    import httpx

    from app.configs.dbConfig import get_db
    from app.main import create_app
    from app.routers.deps import current_scope

    (a_scope, _), (_, b) = two_firms

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[current_scope] = lambda: a_scope

    # httpx's ASGI transport, not TestClient: TestClient drives the app from its
    # own event loop, and the session under test belongs to this one.
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://engine") as client:
        for path in (
            f"/api/v1/jobs/{b['job'].id}",
            f"/status/{b['job'].id}",
            f"/api/v1/mandates/{b['mandate'].id}",
        ):
            r = await client.get(path)
            assert r.status_code == 404, f"{path} answered {r.status_code}"
            assert "not found" in r.json()["detail"].lower()

        # A job that exists nowhere answers identically, so the two cases are
        # indistinguishable from outside.
        missing = await client.get(f"/api/v1/jobs/{uuid.uuid4()}")
        assert missing.status_code == 404


# ── roles ─────────────────────────────────────────────────────────────────────


async def test_an_analyst_cannot_sign_a_valuation(db, two_firms):
    (a_scope, _), _ = two_firms
    analyst = FirmScope(firm_id=a_scope.firm_id, user_id=uuid.uuid4(), role="analyst")

    with pytest.raises(Exception) as excinfo:
        require_sign(analyst)
    assert "may not sign" in str(excinfo.value)

    # An analyst may still do their job.
    require_edit(analyst)


async def test_a_valuer_without_a_registration_cannot_sign(db, two_firms):
    (a_scope, _), _ = two_firms
    unregistered = FirmScope(firm_id=a_scope.firm_id, user_id=uuid.uuid4(), role="valuer")

    with pytest.raises(Exception) as excinfo:
        require_sign(unregistered)
    assert "IBBI registration" in str(excinfo.value)


async def test_a_valuer_registered_for_another_asset_class_cannot_sign(db, two_firms):
    (a_scope, _), _ = two_firms
    valuer = FirmScope(
        firm_id=a_scope.firm_id,
        user_id=uuid.uuid4(),
        role="valuer",
        ibbi_reg_no="IBBI/RV/06/2021/12345",
        valuer_asset_class="plant_and_machinery",
    )

    with pytest.raises(Exception) as excinfo:
        require_sign(valuer, asset_class="land_and_building")
    assert "plant_and_machinery" in str(excinfo.value)

    require_sign(valuer, asset_class="plant_and_machinery")


async def test_a_readonly_user_cannot_create(db, two_firms):
    (a_scope, _), _ = two_firms
    readonly = FirmScope(firm_id=a_scope.firm_id, user_id=uuid.uuid4(), role="readonly")

    with pytest.raises(Exception) as excinfo:
        require_edit(readonly)
    assert "may not create" in str(excinfo.value)


async def test_a_client_user_sees_only_its_granted_mandates(db, two_firms):
    """
    A client is scoped inside its own firm, not just against other firms — it
    reads its mandate and provably nothing else the firm holds.
    """
    (a_scope, a), _ = two_firms

    other_mandate = await mandateRepository.create(
        db, a_scope, client_id=a["client"].id, kind="valuation", purpose="internal"
    )
    client_scope = FirmScope(
        firm_id=a_scope.firm_id,
        user_id=uuid.uuid4(),
        role="client",
        mandate_ids=(a["mandate"].id,),
    )

    visible = {m.id for m in await mandateRepository.list_mandates(db, client_scope)}
    assert visible == {a["mandate"].id}
    assert other_mandate.id not in visible
    assert await mandateRepository.get(db, client_scope, other_mandate.id) is None


async def test_a_client_user_with_no_grants_sees_nothing(db, two_firms):
    """The empty case must fail closed. An empty IN () clause that matches all rows is the bug."""
    (a_scope, _), _ = two_firms
    ungranted = FirmScope(
        firm_id=a_scope.firm_id, user_id=uuid.uuid4(), role="client", mandate_ids=()
    )

    assert await mandateRepository.list_mandates(db, ungranted) == []
    assert await jobRepository.list_jobs(db, ungranted) == []
    assert await propertyRepository.list_properties(db, ungranted) == []
