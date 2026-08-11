"""
Audit router.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.configs.dbConfig import get_db
from app.repositories import auditRepository
from app.routers.deps import current_scope
from app.services.access.scope import FirmScope

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[dict[str, Any]])
async def list_audit_events(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    scope: FirmScope = Depends(current_scope),
):
    events = await auditRepository.list_audit_events(db, scope, limit)
    return [
        {
            "id": str(e.id),
            "actor_id": str(e.actor_id) if e.actor_id else None,
            "action": e.action,
            "resource": e.resource,
            "resource_id": str(e.resource_id) if e.resource_id else None,
            "meta": e.meta,
            "ip": e.ip,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]
