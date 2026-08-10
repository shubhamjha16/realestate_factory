"""
Job routes.

`GET /status/{job_id}` is the prototype's spelling and stays mounted through S5,
then returns 410. `GET /jobs/{job_id}` is the surface in §5 that the console
uses. Both read the same record.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.controllers import generationController
from app.schemas.response.jobResponse import JobStatus

router = APIRouter(tags=["jobs"])


@router.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str) -> JobStatus:
    return generationController.get_job(job_id)


@router.get("/status/{job_id}", response_model=JobStatus, deprecated=True)
def get_status(job_id: str) -> JobStatus:
    return generationController.get_job(job_id)
