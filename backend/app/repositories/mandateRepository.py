"""Mandate repository. Every function is scoped, and a client user sees only its grants."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mandate import Mandate
from app.services.access.scope import FirmScope


def _visible(scope: FirmScope):
    predicate = Mandate.firm_id == scope.firm_id
    if scope.is_client:
        allowed = list(scope.mandate_ids or ())
        if not allowed:
            return predicate & Mandate.id.is_(None)
        predicate = predicate & Mandate.id.in_(allowed)
    return predicate


async def create(
    db: AsyncSession,
    scope: FirmScope,
    *,
    client_id: uuid.UUID,
    kind: str,
    purpose: str,
    instructed_on: date | None = None,
    due_on: date | None = None,
    valuer_id: uuid.UUID | None = None,
) -> Mandate:
    mandate = Mandate(
        firm_id=scope.firm_id,
        client_id=client_id,
        kind=kind,
        purpose=purpose,
        instructed_on=instructed_on,
        due_on=due_on,
        valuer_id=valuer_id,
    )
    db.add(mandate)
    await db.flush()
    await db.commit()
    await db.refresh(mandate)
    return mandate


async def get(db: AsyncSession, scope: FirmScope, mandate_id: uuid.UUID) -> Mandate | None:
    stmt = select(Mandate).where(Mandate.id == mandate_id, _visible(scope))
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_mandates(db: AsyncSession, scope: FirmScope, *, limit: int = 100) -> list[Mandate]:
    stmt = (
        select(Mandate)
        .where(_visible(scope))
        .order_by(Mandate.created_at.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars())
