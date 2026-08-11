"""
Review notes & Sign-Off Gate router (S13).
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.configs.dbConfig import get_db
from app.repositories import auditRepository, deliverableRepository, reviewNoteRepository
from app.routers.deps import current_scope
from app.services.access.authz import require_sign
from app.services.access.scope import FirmScope

router = APIRouter(tags=["review"])


class CreateNoteRequest(BaseModel):
    note: str = Field(..., min_length=1)
    section_id: uuid.UUID | None = None
    comparable_id: uuid.UUID | None = None
    assigned_to: uuid.UUID | None = None


class RespondNoteRequest(BaseModel):
    response: str = Field(..., min_length=1)


class SignDeliverableRequest(BaseModel):
    asset_class: str | None = Field(default="land_and_building")


@router.post("/deliverables/{deliverable_id}/notes", response_model=dict[str, Any])
async def create_review_note(
    deliverable_id: uuid.UUID,
    req: CreateNoteRequest,
    db: AsyncSession = Depends(get_db),
    scope: FirmScope = Depends(current_scope),
):
    deliv = await deliverableRepository.get_deliverable(db, scope, deliverable_id)
    if not deliv:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    note = await reviewNoteRepository.create_note(
        db,
        scope,
        deliverable_id,
        req.note,
        section_id=req.section_id,
        comparable_id=req.comparable_id,
        assigned_to=req.assigned_to,
    )
    return {
        "id": str(note.id),
        "deliverable_id": str(note.deliverable_id),
        "status": note.status,
        "note": note.note,
        "created_at": note.created_at.isoformat() if note.created_at else None,
    }


@router.get("/deliverables/{deliverable_id}/notes", response_model=list[dict[str, Any]])
async def list_review_notes(
    deliverable_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    scope: FirmScope = Depends(current_scope),
):
    notes = await reviewNoteRepository.list_notes(db, scope, deliverable_id)
    return [
        {
            "id": str(n.id),
            "deliverable_id": str(n.deliverable_id),
            "section_id": str(n.section_id) if n.section_id else None,
            "comparable_id": str(n.comparable_id) if n.comparable_id else None,
            "author_id": str(n.author_id) if n.author_id else None,
            "assigned_to": str(n.assigned_to) if n.assigned_to else None,
            "status": n.status,
            "note": n.note,
            "response": n.response,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notes
    ]


@router.post("/notes/{note_id}/respond", response_model=dict[str, Any])
async def respond_review_note(
    note_id: uuid.UUID,
    req: RespondNoteRequest,
    db: AsyncSession = Depends(get_db),
    scope: FirmScope = Depends(current_scope),
):
    note = await reviewNoteRepository.respond_note(db, scope, note_id, req.response)
    if not note:
        raise HTTPException(status_code=404, detail="Review note not found")

    return {
        "id": str(note.id),
        "status": note.status,
        "note": note.note,
        "response": note.response,
    }


@router.post("/notes/{note_id}/close", response_model=dict[str, Any])
async def close_review_note(
    note_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    scope: FirmScope = Depends(current_scope),
):
    note = await reviewNoteRepository.close_note(db, scope, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Review note not found")

    return {
        "id": str(note.id),
        "status": note.status,
    }


@router.post("/deliverables/{deliverable_id}/sign", response_model=dict[str, Any])
async def sign_deliverable(
    deliverable_id: uuid.UUID,
    req: SignDeliverableRequest = SignDeliverableRequest(),
    db: AsyncSession = Depends(get_db),
    scope: FirmScope = Depends(current_scope),
):
    # 1. Sign-off gate authorization: verify registered valuer / partner & asset class
    require_sign(scope, asset_class=req.asset_class)

    # 2. Check for open review notes
    open_notes = await reviewNoteRepository.list_open_notes(db, scope, deliverable_id)
    if open_notes:
        first_open = open_notes[0]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Refused sign-off: deliverable has {len(open_notes)} open review note(s). Open note: {first_open.note!r}",
        )

    # 3. Update deliverable status
    deliv = await deliverableRepository.get_deliverable(db, scope, deliverable_id)
    if not deliv:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    deliv.status = "signed"
    deliv.signed_by = scope.user_id
    deliv.signed_at = datetime.datetime.now(datetime.UTC)
    db.add(deliv)
    await db.flush()

    # 4. Log audit event
    await auditRepository.record_audit_event(
        db,
        scope=scope,
        action="sign_deliverable",
        resource="deliverable",
        resource_id=deliv.id,
        meta={"asset_class": req.asset_class, "signer_ibbi_reg_no": scope.ibbi_reg_no},
    )

    return {
        "id": str(deliv.id),
        "status": deliv.status,
        "signed_by": str(deliv.signed_by),
        "signed_at": deliv.signed_at.isoformat() if deliv.signed_at else None,
    }
