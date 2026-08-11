"""
Audit repository.

Logs and retrieves firm-scoped audit events for reads, provenance lookups, and exports.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auditEvent import AuditEvent
from app.services.access.scope import FirmScope


async def record_audit_event(
    db: AsyncSession,
    scope: FirmScope,
    action: str,
    resource: str,
    *,
    resource_id: uuid.UUID | None = None,
    meta: dict[str, Any] | None = None,
    ip: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        firm_id=scope.firm_id,
        actor_id=scope.user_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        meta=meta,
        ip=ip,
    )
    db.add(event)
    await db.flush()
    return event


async def list_audit_events(
    db: AsyncSession, scope: FirmScope, limit: int = 50
) -> Sequence[AuditEvent]:
    stmt = (
        select(AuditEvent)
        .where(AuditEvent.firm_id == scope.firm_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    return res.scalars().all()
