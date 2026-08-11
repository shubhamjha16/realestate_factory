"""
Generation controller — validate, persist the job, hand it to the service.

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
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def start_generation(db: AsyncSession, req: GenerateRequest) -> JobStatus:
    job = await jobRepository.create(
        db,
        job_type=req.job_type or "",
        instructions=req.instructions,
    )
    generationService.run_in_background(job.id, req.instructions, req.property_data, req.job_type)
    logger.info("job %s queued | type: %s", job.id, req.job_type)
    return JobStatus.of(job)


async def get_job(db: AsyncSession, job_id: str) -> JobStatus:
    job = await jobRepository.get(db, _as_uuid(job_id))
    if job is None:
        raise HTTPException(404, "Job not found")
    return JobStatus.of(job)


def _as_uuid(job_id: str) -> uuid.UUID:
    """
    A malformed id is a 404, not a 422. It is indistinguishable from an id that
    does not exist, and from S5 a cross-firm id must also be a 404 — so every
    "no such job" answer looks the same and none of them leaks.
    """
    try:
        return uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(404, "Job not found") from None
