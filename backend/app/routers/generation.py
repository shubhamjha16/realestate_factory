"""Generation route."""

from __future__ import annotations

from fastapi import APIRouter

from app.controllers import generationController
from app.schemas.request.generateRequest import GenerateRequest
from app.schemas.response.jobResponse import JobStatus

router = APIRouter(tags=["generation"])


@router.post("/generate", response_model=JobStatus)
def generate(req: GenerateRequest) -> JobStatus:
    return generationController.start_generation(req)
