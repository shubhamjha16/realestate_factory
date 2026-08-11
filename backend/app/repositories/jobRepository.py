"""
Job repository.

Every function that answers a caller takes a `FirmScope` and filters by it.
There is exactly one unscoped reader, `get_unscoped`, and it exists for the arq
worker, which has a job id from the queue and no user session. It is named so it
cannot be reached for by accident and so the guard test can allow it explicitly.

Cross-firm reads return `None`, and the controller turns that into a 404. Not
403: "you may not read this" confirms the row exists, and for a mandate name or
a property address that confirmation is itself the leak.

**Terminal finality.** Once `terminal_at` is set, this layer refuses any further
write to `status`, `doc_url` or `error`. Enforced here because there are several
writers — the web process, the arq worker, S13's retention sweep — and a rule
that lives in one caller is a rule the next caller does not know about. A
completed deliverable that later flips to `failed` is a record a bank cannot
rely on.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import TERMINAL_STATUSES, Job
from app.services.access.scope import FirmScope


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


def _visible(scope: FirmScope):
    """
    The tenancy predicate, in one place.

    A `client` user sees the mandates they were granted and nothing else — not
    their firm's other work, and never another firm's.
    """
    predicate = Job.firm_id == scope.firm_id
    if scope.is_client:
        allowed = list(scope.mandate_ids or ())
        if not allowed:
            # No grants means nothing visible, not everything visible.
            return predicate & Job.id.is_(None)
        predicate = predicate & Job.mandate_id.in_(allowed)
    return predicate


async def create(
    db: AsyncSession,
    scope: FirmScope,
    *,
    job_type: str = "",
    instructions: str = "",
    mandate_id: uuid.UUID | None = None,
    idempotency_key: str | None = None,
) -> Job:
    job = Job(
        status="queued",
        job_type=job_type,
        instructions=instructions,
        firm_id=scope.firm_id,
        user_id=scope.user_id,
        mandate_id=mandate_id,
        idempotency_key=idempotency_key,
    )
    db.add(job)
    await db.flush()
    await db.commit()
    await db.refresh(job)
    return job


async def get(db: AsyncSession, scope: FirmScope, job_id: uuid.UUID) -> Job | None:
    stmt = select(Job).where(Job.id == job_id, _visible(scope))
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_jobs(db: AsyncSession, scope: FirmScope, *, limit: int = 50) -> list[Job]:
    stmt = select(Job).where(_visible(scope)).order_by(Job.created_at.desc()).limit(limit)
    return list((await db.execute(stmt)).scalars())


async def search(db: AsyncSession, scope: FirmScope, term: str, *, limit: int = 50) -> list[Job]:
    """
    Search is a read like any other, and the most commonly forgotten one — the
    listing endpoint gets scoped and the search beside it does not.
    """
    stmt = (
        select(Job)
        .where(_visible(scope), Job.instructions.ilike(f"%{term}%"))
        .order_by(Job.created_at.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars())


async def find_by_idempotency_key(db: AsyncSession, scope: FirmScope, key: str) -> Job | None:
    """
    The key already contains the firm id, so a cross-firm collision is not
    possible — but this still filters by scope, because a repository function
    that trusts its input to be pre-scoped is one refactor away from not being.
    """
    stmt = select(Job).where(Job.idempotency_key == key, _visible(scope))
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_unscoped(db: AsyncSession, job_id: uuid.UUID) -> Job | None:
    """
    For the worker only.

    arq hands it a job id and no session; there is no user to scope by. Every
    other reader must use `get`. `tests/test_repository_scope_guard.py` allows
    this name and no other.
    """
    return await db.get(Job, job_id)


async def set_status(
    db: AsyncSession,
    job_id: uuid.UUID,
    status: str,
    *,
    doc_url: str | None = None,
    error: str | None = None,
) -> Job:
    """
    The only way a job's status changes. Unscoped: the worker owns this
    transition and has no session. It is a write to a specific known id, never a
    read that could return another firm's row.

    Guarded twice on purpose. The read-then-check produces an error naming when
    the job finished; the `terminal_at IS NULL` predicate on the UPDATE makes it
    safe against a second worker racing between the two.
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
    Jobs left `processing` by a worker that died without arq redelivering.

    Unscoped and deliberately so: operational, runs on a schedule with no user,
    and returns a count rather than any row.
    """
    stmt = select(Job).where(
        Job.status == "processing",
        Job.terminal_at.is_(None),
        Job.created_at < older_than,
    )
    return len(list((await db.execute(stmt)).scalars()))
