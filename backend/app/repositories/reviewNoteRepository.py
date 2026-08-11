"""
Review note repository.

Manages firm-scoped review notes, responses, closures, and open-note queries.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reviewNote import ReviewNote
from app.services.access.scope import FirmScope


async def create_note(
    db: AsyncSession,
    scope: FirmScope,
    deliverable_id: uuid.UUID,
    note: str,
    *,
    section_id: uuid.UUID | None = None,
    comparable_id: uuid.UUID | None = None,
    assigned_to: uuid.UUID | None = None,
) -> ReviewNote:
    r_note = ReviewNote(
        firm_id=scope.firm_id,
        deliverable_id=deliverable_id,
        section_id=section_id,
        comparable_id=comparable_id,
        author_id=scope.user_id,
        assigned_to=assigned_to,
        status="open",
        note=note,
    )
    db.add(r_note)
    await db.flush()
    return r_note


async def get_note(
    db: AsyncSession, scope: FirmScope, note_id: uuid.UUID
) -> ReviewNote | None:
    stmt = select(ReviewNote).where(
        ReviewNote.id == note_id, ReviewNote.firm_id == scope.firm_id
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def respond_note(
    db: AsyncSession, scope: FirmScope, note_id: uuid.UUID, response_text: str
) -> ReviewNote | None:
    r_note = await get_note(db, scope, note_id)
    if not r_note:
        return None
    r_note.response = response_text
    r_note.status = "responded"
    db.add(r_note)
    await db.flush()
    return r_note


async def close_note(
    db: AsyncSession, scope: FirmScope, note_id: uuid.UUID
) -> ReviewNote | None:
    r_note = await get_note(db, scope, note_id)
    if not r_note:
        return None
    r_note.status = "closed"
    db.add(r_note)
    await db.flush()
    return r_note


async def list_notes(
    db: AsyncSession, scope: FirmScope, deliverable_id: uuid.UUID
) -> Sequence[ReviewNote]:
    stmt = (
        select(ReviewNote)
        .where(
            ReviewNote.deliverable_id == deliverable_id,
            ReviewNote.firm_id == scope.firm_id,
        )
        .order_by(ReviewNote.created_at.asc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()


async def list_open_notes(
    db: AsyncSession, scope: FirmScope, deliverable_id: uuid.UUID
) -> Sequence[ReviewNote]:
    stmt = (
        select(ReviewNote)
        .where(
            ReviewNote.deliverable_id == deliverable_id,
            ReviewNote.firm_id == scope.firm_id,
            ReviewNote.status.in_(["open", "responded"]),
        )
        .order_by(ReviewNote.created_at.asc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()
