"""Client controller."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import clientRepository
from app.schemas.request.authRequest import CreateClientRequest
from app.schemas.response.authResponse import ClientResponse
from app.services.access.authz import require_edit
from app.services.access.scope import FirmScope


def _shape(client) -> ClientResponse:
    return ClientResponse(id=str(client.id), name=client.name, kind=client.kind)


async def create(db: AsyncSession, scope: FirmScope, req: CreateClientRequest) -> ClientResponse:
    require_edit(scope)
    return _shape(await clientRepository.create(db, scope, name=req.name, kind=req.kind))


async def list_clients(db: AsyncSession, scope: FirmScope) -> list[ClientResponse]:
    return [_shape(c) for c in await clientRepository.list_clients(db, scope)]


async def search(db: AsyncSession, scope: FirmScope, term: str) -> list[ClientResponse]:
    return [_shape(c) for c in await clientRepository.search(db, scope, term)]
