"""
Documents and the evidence behind an assertion.

`bundle_for` is the only function the evidence gate needs: it collapses four
tables into the shape `evidenceValidator.EvidenceBundle` reads, so the gate has
no database access of its own and can be tested without one.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.propertyDocument import (
    Approval,
    Encumbrance,
    PropertyDocument,
    TitleChainEntry,
)
from app.services.access.scope import FirmScope
from app.validators.evidenceValidator import EvidenceBundle


async def list_documents(
    db: AsyncSession, scope: FirmScope, property_id: uuid.UUID
) -> list[PropertyDocument]:
    stmt = (
        select(PropertyDocument)
        .where(
            PropertyDocument.property_id == property_id,
            PropertyDocument.firm_id == scope.firm_id,
        )
        .order_by(PropertyDocument.doc_date.desc().nullslast())
    )
    return list((await db.execute(stmt)).scalars())


async def list_title_chain(
    db: AsyncSession, scope: FirmScope, property_id: uuid.UUID
) -> list[TitleChainEntry]:
    stmt = (
        select(TitleChainEntry)
        .where(
            TitleChainEntry.property_id == property_id,
            TitleChainEntry.firm_id == scope.firm_id,
        )
        .order_by(TitleChainEntry.ord)
    )
    return list((await db.execute(stmt)).scalars())


async def list_encumbrances(
    db: AsyncSession, scope: FirmScope, property_id: uuid.UUID
) -> list[Encumbrance]:
    stmt = select(Encumbrance).where(
        Encumbrance.property_id == property_id, Encumbrance.firm_id == scope.firm_id
    )
    return list((await db.execute(stmt)).scalars())


async def list_approvals(
    db: AsyncSession, scope: FirmScope, property_id: uuid.UUID
) -> list[Approval]:
    stmt = select(Approval).where(
        Approval.property_id == property_id, Approval.firm_id == scope.firm_id
    )
    return list((await db.execute(stmt)).scalars())


async def bundle_for(
    db: AsyncSession, scope: FirmScope, property_id: uuid.UUID
) -> EvidenceBundle:
    """
    Everything the gate needs, in one shape.

    A chain "gap" is an `ord` sequence that is not contiguous from 1: a chain
    missing its middle link is not a chain, and a report must not call what it
    describes marketable.
    """
    documents = await list_documents(db, scope, property_id)
    chain = await list_title_chain(db, scope, property_id)
    encumbrances = await list_encumbrances(db, scope, property_id)
    approvals = await list_approvals(db, scope, property_id)

    orders = sorted(e.ord for e in chain)
    has_gap = bool(orders) and orders != list(range(orders[0], orders[0] + len(orders)))

    by_kind: dict[str, list[str]] = {}
    for document in documents:
        by_kind.setdefault(document.kind, []).append(str(document.id))

    return EvidenceBundle(
        property_id=str(property_id),
        document_kinds=frozenset(by_kind),
        title_chain_length=len(chain),
        title_chain_has_gap=has_gap,
        encumbrance_count=len(encumbrances),
        subsisting_encumbrance_count=sum(1 for e in encumbrances if e.is_subsisting),
        approval_kinds=frozenset(a.kind for a in approvals),
        expired_approval_kinds=frozenset(),
        document_ids_by_kind=by_kind,
    )
