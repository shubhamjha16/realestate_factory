"""
Job routes.

`GET /status/{job_id}` is the prototype's spelling and stays mounted through S5,
then returns 410. `GET /jobs/{job_id}` is the surface in §5 that the console
uses. Both read the same record, both through the caller's scope.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.configs.dbConfig import get_db
from app.controllers import generationController
from app.routers.deps import current_scope
from app.schemas.response.jobResponse import JobStatus
from app.services.access.scope import FirmScope

router = APIRouter(tags=["jobs"])


@router.get("/jobs", response_model=list[JobStatus])
async def list_jobs(
    q: str | None = Query(default=None),
    scope: FirmScope = Depends(current_scope),
    db: AsyncSession = Depends(get_db),
) -> list[JobStatus]:
    return await generationController.list_jobs(db, scope, q)


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job(
    job_id: str,
    scope: FirmScope = Depends(current_scope),
    db: AsyncSession = Depends(get_db),
) -> JobStatus:
    return await generationController.get_job(db, scope, job_id)


@router.get("/status/{job_id}", response_model=JobStatus, deprecated=True)
async def get_status(
    job_id: str,
    scope: FirmScope = Depends(current_scope),
    db: AsyncSession = Depends(get_db),
) -> JobStatus:
    return await generationController.get_job(db, scope, job_id)
