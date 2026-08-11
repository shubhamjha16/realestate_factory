"""
Deliverables router.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.configs.dbConfig import get_db
from app.controllers import deliverableController
from app.routers.deps import current_scope
from app.services.access.scope import FirmScope

router = APIRouter(prefix="/deliverables", tags=["deliverables"])


@router.get("", response_model=list[dict[str, Any]])
async def list_deliverables(
    mandate_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    scope: FirmScope = Depends(current_scope),
):
    return await deliverableController.list_deliverables(db, scope, mandate_id)


@router.get("/{deliverable_id}", response_model=dict[str, Any])
async def get_deliverable(
    deliverable_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    scope: FirmScope = Depends(current_scope),
):
    res = await deliverableController.get_deliverable(db, scope, deliverable_id)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deliverable not found")
    return res


@router.get("/{deliverable_id}/provenance", response_model=dict[str, Any])
async def get_provenance(
    deliverable_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    scope: FirmScope = Depends(current_scope),
):
    res = await deliverableController.get_provenance(db, scope, deliverable_id)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deliverable not found")
    return res
