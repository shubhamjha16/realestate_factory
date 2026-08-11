"""
Property repository.

`search_nearby` is the spatial query the GiST index on `properties.geom` exists
for. It is scoped like every other read: a comparable search that reached across
a firm boundary would leak both the existence and the location of another firm's
instructed property.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.property import Property
from app.services.access.scope import FirmScope


def _visible(scope: FirmScope):
    predicate = Property.firm_id == scope.firm_id
    if scope.is_client:
        allowed = list(scope.mandate_ids or ())
        if not allowed:
            return predicate & Property.id.is_(None)
        predicate = predicate & Property.mandate_id.in_(allowed)
    return predicate


async def create(
    db: AsyncSession,
    scope: FirmScope,
    *,
    title: str,
    mandate_id: uuid.UUID | None = None,
    **fields,
) -> Property:
    prop = Property(firm_id=scope.firm_id, mandate_id=mandate_id, title=title, **fields)
    db.add(prop)
    await db.flush()
    await db.commit()
    await db.refresh(prop)
    return prop


async def get(db: AsyncSession, scope: FirmScope, property_id: uuid.UUID) -> Property | None:
    stmt = select(Property).where(Property.id == property_id, _visible(scope))
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_properties(db: AsyncSession, scope: FirmScope, *, limit: int = 100) -> list[Property]:
    stmt = (
        select(Property)
        .where(_visible(scope))
        .order_by(Property.created_at.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars())


async def search(db: AsyncSession, scope: FirmScope, term: str, *, limit: int = 50) -> list[Property]:
    like = f"%{term}%"
    stmt = (
        select(Property)
        .where(
            _visible(scope),
            Property.title.ilike(like) | Property.address.ilike(like) | Property.locality.ilike(like),
        )
        .order_by(Property.created_at.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars())


async def search_nearby(
    db: AsyncSession,
    scope: FirmScope,
    *,
    lat: float,
    lng: float,
    radius_m: int,
    limit: int = 100,
) -> list[Property]:
    """
    `ST_DWithin` on a geography column, which uses the GiST index hand-added in
    revision 0001. Without that index this is a sequential scan that still
    returns the right rows — which is why its absence goes unnoticed until the
    table is large enough that fixing it is disruptive.
    """
    point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326).cast(Property.geom.type)
    stmt = (
        select(Property)
        .where(
            _visible(scope),
            Property.geom.isnot(None),
            func.ST_DWithin(Property.geom, point, radius_m),
        )
        .order_by(func.ST_Distance(Property.geom, point))
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars())
