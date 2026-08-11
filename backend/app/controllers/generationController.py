"""
Generation controller — validate, deduplicate, persist, enqueue.

Routers hold no logic and no store access; controllers hold no SQL.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import jobRepository
from app.schemas.request.generateRequest import GenerateRequest
from app.schemas.response.jobResponse import JobStatus
from app.services import generationService
from app.services.access.authz import require_edit
from app.services.access.scope import FirmScope
from app.utils.idempotency import build_key
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def start_generation(db: AsyncSession, scope: FirmScope, req: GenerateRequest) -> JobStatus:
    require_edit(scope)

    key = build_key(
        firm_id=scope.firm_id,
        job_type=req.job_type,
        instructions=req.instructions,
        import_checksums=req.import_checksums(),
    )

    # A retried submit is the same job, not a second one. Without this a dropped
    # connection costs a duplicate deliverable, a duplicate ledger entry, and two
    # documents a reviewer has to tell apart.
    existing = await jobRepository.find_by_idempotency_key(db, scope, key)
    if existing is not None:
        logger.info("returning existing job %s for a repeated submission", existing.id)
        return JobStatus.of(existing)

    job = await jobRepository.create(
        db,
        scope,
        job_type=req.job_type or "",
        instructions=req.instructions,
        idempotency_key=key,
    )
    await generationService.enqueue(job.id, req.instructions, req.property_data, req.job_type)
    logger.info("job %s queued | type: %s", job.id, req.job_type)
    return JobStatus.of(job)


async def get_job(db: AsyncSession, scope: FirmScope, job_id: str) -> JobStatus:
    job = await jobRepository.get(db, scope, _as_uuid(job_id))
    if job is None:
        raise HTTPException(404, "Job not found")
    return JobStatus.of(job)


async def list_jobs(db: AsyncSession, scope: FirmScope, term: str | None = None) -> list[JobStatus]:
    jobs = (
        await jobRepository.search(db, scope, term)
        if term
        else await jobRepository.list_jobs(db, scope)
    )
    return [JobStatus.of(j) for j in jobs]


def _as_uuid(job_id: str) -> uuid.UUID:
    """
    A malformed id is a 404, not a 422. It is indistinguishable from an id that
    does not exist, and a cross-firm id must also be a 404 — so every "no such
    job" answer looks the same and none of them leaks.
    """
    try:
        return uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(404, "Job not found") from None
