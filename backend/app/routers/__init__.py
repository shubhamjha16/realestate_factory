"""
Route aggregation.

`api_router` is the `/api/v1` surface of §5, which the console consumes.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.routers import (
    audit,
    auth,
    clients,
    compliance,
    deliverables,
    events,
    export,
    generation,
    health,
    jobs,
    mandates,
    portfolio,
    retrieval,
    reviewNotes,
    webhooks,
)

api_router = APIRouter(prefix="/api/v1")
for _router in (
    auth.router,
    health.router,
    clients.router,
    mandates.router,
    generation.router,
    jobs.router,
    deliverables.router,
    audit.router,
    reviewNotes.router,
    compliance.router,
    export.router,
    portfolio.router,
    retrieval.router,
    webhooks.router,
    events.router,
):
    api_router.include_router(_router)

legacy_router = APIRouter()
for _router in (health.router, generation.router, jobs.router):
    legacy_router.include_router(_router)

__all__ = ["api_router", "legacy_router"]
