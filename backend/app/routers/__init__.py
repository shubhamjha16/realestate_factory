"""
Route aggregation.

`api_router` is the `/api/v1` surface of §5, which the console consumes.
`legacy_router` is the prototype's unprefixed spelling — `POST /generate`,
`GET /status/{job_id}`, `GET /health` — mounted at the root so that S1 breaks no
existing caller. §5 keeps it through S5, after which it returns 410.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.routers import generation, health, jobs

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(generation.router)
api_router.include_router(jobs.router)

legacy_router = APIRouter()
legacy_router.include_router(health.router)
legacy_router.include_router(generation.router)
legacy_router.include_router(jobs.router)

__all__ = ["api_router", "legacy_router"]
