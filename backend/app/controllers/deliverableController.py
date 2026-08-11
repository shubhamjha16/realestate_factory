"""
Deliverable controller.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import auditRepository, deliverableRepository
from app.services.access.scope import FirmScope


async def list_deliverables(
    db: AsyncSession, scope: FirmScope, mandate_id: uuid.UUID | None = None
) -> list[dict[str, Any]]:
    delivs = await deliverableRepository.list_deliverables(db, scope, mandate_id)
    return [
        {
            "id": str(d.id),
            "doc_type": d.doc_type,
            "title": d.title,
            "status": d.status,
            "mandate_id": str(d.mandate_id) if d.mandate_id else None,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in delivs
    ]


async def get_deliverable(
    db: AsyncSession, scope: FirmScope, deliverable_id: uuid.UUID
) -> dict[str, Any] | None:
    deliv = await deliverableRepository.get_deliverable(db, scope, deliverable_id)
    if not deliv:
        return None

    # Log audit event for reading deliverable
    await auditRepository.record_audit_event(
        db,
        scope=scope,
        action="read_deliverable",
        resource="deliverable",
        resource_id=deliv.id,
    )

    return {
        "id": str(deliv.id),
        "doc_type": deliv.doc_type,
        "title": deliv.title,
        "status": deliv.status,
        "current_version": deliv.current_version,
        "sections": [
            {
                "id": str(s.id),
                "ord": s.ord,
                "section_type": s.section_type,
                "content": s.content,
            }
            for s in deliv.sections
        ],
    }


async def get_provenance(
    db: AsyncSession, scope: FirmScope, deliverable_id: uuid.UUID
) -> dict[str, Any] | None:
    prov = await deliverableRepository.get_provenance(db, scope, deliverable_id)
    if not prov:
        return None

    # Log audit event for provenance lookup
    await auditRepository.record_audit_event(
        db,
        scope=scope,
        action="fetch_provenance",
        resource="deliverable",
        resource_id=deliverable_id,
    )

    return prov
