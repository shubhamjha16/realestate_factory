"""Mandate routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.configs.dbConfig import get_db
from app.controllers import mandateController
from app.routers.deps import current_scope
from app.schemas.request.authRequest import CreateMandateRequest
from app.schemas.response.authResponse import MandateResponse
from app.services.access.scope import FirmScope

router = APIRouter(tags=["mandates"])


@router.post("/mandates", response_model=MandateResponse, status_code=201)
async def create_mandate(
    req: CreateMandateRequest,
    scope: FirmScope = Depends(current_scope),
    db: AsyncSession = Depends(get_db),
) -> MandateResponse:
    return await mandateController.create(db, scope, req)


@router.get("/mandates", response_model=list[MandateResponse])
async def list_mandates(
    scope: FirmScope = Depends(current_scope),
    db: AsyncSession = Depends(get_db),
) -> list[MandateResponse]:
    return await mandateController.list_mandates(db, scope)


@router.get("/mandates/{mandate_id}", response_model=MandateResponse)
async def get_mandate(
    mandate_id: str,
    scope: FirmScope = Depends(current_scope),
    db: AsyncSession = Depends(get_db),
) -> MandateResponse:
    return await mandateController.get(db, scope, mandate_id)
