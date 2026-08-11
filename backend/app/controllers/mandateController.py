"""Mandate controller."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import clientRepository, mandateRepository
from app.schemas.request.authRequest import CreateMandateRequest
from app.schemas.response.authResponse import MandateResponse
from app.services.access.authz import require_edit
from app.services.access.scope import FirmScope


def _shape(mandate) -> MandateResponse:
    return MandateResponse(
        id=str(mandate.id),
        client_id=str(mandate.client_id),
        kind=mandate.kind,
        purpose=mandate.purpose,
        status=mandate.status,
        instructed_on=mandate.instructed_on,
        due_on=mandate.due_on,
        valuer_id=str(mandate.valuer_id) if mandate.valuer_id else None,
        created_at=mandate.created_at,
        requires_registered_valuer=mandate.requires_registered_valuer,
    )


async def create(db: AsyncSession, scope: FirmScope, req: CreateMandateRequest) -> MandateResponse:
    require_edit(scope)

    # The client is looked up *through the scope*, so naming another firm's
    # client id reads as "no such client" rather than creating a mandate that
    # points across the boundary.
    client = await clientRepository.get(db, scope, _as_uuid(req.client_id))
    if client is None:
        raise HTTPException(404, "Client not found")

    mandate = await mandateRepository.create(
        db,
        scope,
        client_id=client.id,
        kind=req.kind,
        purpose=req.purpose,
        instructed_on=_as_date(req.instructed_on),
        due_on=_as_date(req.due_on),
        valuer_id=_as_uuid(req.valuer_id) if req.valuer_id else None,
    )
    return _shape(mandate)


async def get(db: AsyncSession, scope: FirmScope, mandate_id: str) -> MandateResponse:
    mandate = await mandateRepository.get(db, scope, _as_uuid(mandate_id))
    if mandate is None:
        raise HTTPException(404, "Mandate not found")
    return _shape(mandate)


async def list_mandates(db: AsyncSession, scope: FirmScope) -> list[MandateResponse]:
    return [_shape(m) for m in await mandateRepository.list_mandates(db, scope)]


def _as_uuid(value: str) -> uuid.UUID:
    """A malformed id is a 404: indistinguishable from one that does not exist."""
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(404, "Not found") from None


def _as_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(422, f"{value!r} is not an ISO date (YYYY-MM-DD)") from None
