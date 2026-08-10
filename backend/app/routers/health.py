"""Health route."""

from __future__ import annotations

from fastapi import APIRouter

from app.controllers import healthController

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return healthController.health()
