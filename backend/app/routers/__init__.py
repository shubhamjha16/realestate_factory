"""
Route aggregation.

`api_router` is the `/api/v1` surface of §5, which the console consumes.
`legacy_router` is the prototype's unprefixed spelling — `POST /generate`,
`GET /status/{job_id}`, `GET /health` — mounted at the root so that S1 breaks no
existing caller. §5 keeps it through S5, after which it returns 410.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.routers import auth, clients, generation, health, jobs, mandates

api_router = APIRouter(prefix="/api/v1")
for _router in (auth.router, health.router, clients.router, mandates.router,
                generation.router, jobs.router):
    api_router.include_router(_router)

# The prototype's unprefixed spelling. Everything but /health now requires a
# session like its /api/v1 twin — an unauthenticated alias would be a way around
# tenancy, which is the one thing S5 exists to prevent.
legacy_router = APIRouter()
for _router in (health.router, generation.router, jobs.router):
    legacy_router.include_router(_router)

__all__ = ["api_router", "legacy_router"]
