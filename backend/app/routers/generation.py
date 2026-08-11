"""Generation route."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.configs.dbConfig import get_db
from app.controllers import generationController
from app.routers.deps import current_scope
from app.schemas.request.generateRequest import GenerateRequest
from app.schemas.response.jobResponse import JobStatus
from app.services.access.scope import FirmScope

router = APIRouter(tags=["generation"])


@router.post("/generate", response_model=JobStatus, status_code=202)
async def generate(
    req: GenerateRequest,
    scope: FirmScope = Depends(current_scope),
    db: AsyncSession = Depends(get_db),
) -> JobStatus:
    return await generationController.start_generation(db, scope, req)
