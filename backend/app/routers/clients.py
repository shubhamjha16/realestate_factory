"""Client routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.configs.dbConfig import get_db
from app.controllers import clientController
from app.routers.deps import current_scope
from app.schemas.request.authRequest import CreateClientRequest
from app.schemas.response.authResponse import ClientResponse
from app.services.access.scope import FirmScope

router = APIRouter(tags=["clients"])


@router.post("/clients", response_model=ClientResponse, status_code=201)
async def create_client(
    req: CreateClientRequest,
    scope: FirmScope = Depends(current_scope),
    db: AsyncSession = Depends(get_db),
) -> ClientResponse:
    return await clientController.create(db, scope, req)


@router.get("/clients", response_model=list[ClientResponse])
async def list_clients(
    q: str | None = Query(default=None),
    scope: FirmScope = Depends(current_scope),
    db: AsyncSession = Depends(get_db),
) -> list[ClientResponse]:
    if q:
        return await clientController.search(db, scope, q)
    return await clientController.list_clients(db, scope)
