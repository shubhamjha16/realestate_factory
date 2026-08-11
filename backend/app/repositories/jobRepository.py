"""
Job repository — Postgres.

Replaces `jobs.json` and `threading.Lock`. A restart no longer loses in-flight
work: a job that was mid-graph when the process died is still `processing` in
the database and can be swept (S4 adds the sweep).

**Terminal finality.** Once `terminal_at` is set, this layer refuses any further
write to `status`, `doc_url` or `error`. It is enforced here rather than in a
service because there will be several writers — the web process today, the arq
worker from S4, the retention sweep from S13 — and a rule that lives in one
caller is a rule the next caller does not know about. A completed deliverable
that later flips to `failed` is a record a bank cannot rely on.

From S5 every method here takes a firm scope, and none is callable without one.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import TERMINAL_STATUSES, Job


class TerminalJobError(RuntimeError):
    """Raised when a write is attempted against a job that has already finished."""

    def __init__(self, job_id: uuid.UUID, terminal_at: datetime, attempted: str):
        self.job_id = job_id
        self.terminal_at = terminal_at
        self.attempted = attempted
        super().__init__(
            f"job {job_id} reached a terminal state at {terminal_at.isoformat()}; "
            f"refusing to set status={attempted!r}"
        )


async def create(
    db: AsyncSession,
    *,
    job_type: str = "",
    instructions: str = "",
    firm_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    idempotency_key: str | None = None,
) -> Job:
    job = Job(
        status="queued",
        job_type=job_type,
        instructions=instructions,
        firm_id=firm_id,
        user_id=user_id,
        idempotency_key=idempotency_key,
    )
    db.add(job)
    await db.flush()
    await db.commit()
    await db.refresh(job)
    return job


async def get(db: AsyncSession, job_id: uuid.UUID) -> Job | None:
    return await db.get(Job, job_id)


async def list_for_firm(db: AsyncSession, firm_id: uuid.UUID | None, limit: int = 50) -> list[Job]:
    stmt = select(Job).order_by(Job.created_at.desc()).limit(limit)
    # S5 makes the scope mandatory rather than conditional.
    if firm_id is not None:
        stmt = stmt.where(Job.firm_id == firm_id)
    return list((await db.execute(stmt)).scalars())


async def set_status(
    db: AsyncSession,
    job_id: uuid.UUID,
    status: str,
    *,
    doc_url: str | None = None,
    error: str | None = None,
) -> Job:
    """
    The only way a job's status changes.

    Guarded twice on purpose. The read-then-check gives a useful error naming
    when the job finished; the `terminal_at IS NULL` predicate in the UPDATE
    makes it safe against a concurrent writer between the two, which is exactly
    the race that arrives with the worker in S4.
    """
    job = await db.get(Job, job_id)
    if job is None:
        raise LookupError(f"job {job_id} not found")
    if job.terminal_at is not None:
        raise TerminalJobError(job_id, job.terminal_at, status)

    values: dict = {"status": status}
    if doc_url is not None:
        values["doc_url"] = doc_url
    if error is not None:
        values["error"] = error
    if status in TERMINAL_STATUSES:
        values["terminal_at"] = datetime.now(UTC)

    result = await db.execute(
        update(Job)
        .where(Job.id == job_id, Job.terminal_at.is_(None))
        .values(**values)
        .returning(Job.id)
    )
    if result.scalar_one_or_none() is None:
        # Another writer terminated it between the read and the update. That is
        # the race the `terminal_at IS NULL` predicate exists to lose safely.
        await db.rollback()
        fresh = await db.get(Job, job_id)
        if fresh is None:
            raise LookupError(f"job {job_id} not found")
        raise TerminalJobError(job_id, fresh.terminal_at or datetime.now(UTC), status)

    await db.commit()
    await db.refresh(job)
    return job


async def reconcile_orphans(db: AsyncSession, older_than: datetime) -> int:
    """
    Jobs left `processing` by a killed process.

    S1 lost these entirely — the file was rewritten on restart. They are now
    visible and countable, which is what makes them reconcilable. S4's worker
    owns deciding their fate; this only reports them.
    """
    stmt = select(Job).where(
        Job.status == "processing",
        Job.terminal_at.is_(None),
        Job.created_at < older_than,
    )
    return len(list((await db.execute(stmt)).scalars()))
