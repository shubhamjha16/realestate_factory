"""
Generation controller — validate, create the job, hand it to the service.

Routers hold no logic and no store access; controllers hold no SQL.
"""

from __future__ import annotations

from fastapi import HTTPException

from app.repositories import jobRepository
from app.schemas.request.generateRequest import GenerateRequest
from app.schemas.response.jobResponse import JobStatus
from app.services import generationService
from app.utils.logger import get_logger
from app.validators.generateValidator import validate_generate

logger = get_logger(__name__)


def start_generation(req: GenerateRequest) -> JobStatus:
    validate_generate(req)

    job_id = generationService.new_job_id()
    record = jobRepository.create(job_id, job_type=req.job_type or "")

    generationService.run_in_background(job_id, req.instructions, req.property_data, req.job_type)

    logger.info("job %s queued | type: %s", job_id, req.job_type)
    return JobStatus(**record)


def get_job(job_id: str) -> JobStatus:
    record = jobRepository.get(job_id)
    if record is None:
        raise HTTPException(404, "Job not found")
    return JobStatus(**record)
