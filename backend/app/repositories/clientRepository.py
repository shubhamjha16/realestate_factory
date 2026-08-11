"""Client repository. Every function is scoped."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.services.access.scope import FirmScope


async def create(db: AsyncSession, scope: FirmScope, *, name: str, kind: str) -> Client:
    client = Client(firm_id=scope.firm_id, name=name.strip(), kind=kind)
    db.add(client)
    await db.flush()
    await db.commit()
    await db.refresh(client)
    return client


async def get(db: AsyncSession, scope: FirmScope, client_id: uuid.UUID) -> Client | None:
    stmt = select(Client).where(Client.id == client_id, Client.firm_id == scope.firm_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_clients(db: AsyncSession, scope: FirmScope, *, limit: int = 100) -> list[Client]:
    stmt = (
        select(Client)
        .where(Client.firm_id == scope.firm_id)
        .order_by(Client.name)
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars())


async def search(db: AsyncSession, scope: FirmScope, term: str, *, limit: int = 50) -> list[Client]:
    stmt = (
        select(Client)
        .where(Client.firm_id == scope.firm_id, Client.name.ilike(f"%{term}%"))
        .order_by(Client.name)
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars())
