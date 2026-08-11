"""
Deliverable repository.

Provides firm-scoped queries for deliverables, sections, and the S12 provenance chain
resolution (section -> figure -> comparable and section -> document).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.comparable import Comparable
from app.models.deliverable import Deliverable, DeliverableSection, DeliverableVersion
from app.models.propertyDocument import PropertyDocument
from app.models.valuation import ValuationLine
from app.services.access.scope import FirmScope


async def create_deliverable(
    db: AsyncSession,
    scope: FirmScope,
    doc_type: str,
    title: str,
    *,
    mandate_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    s3_key: str | None = None,
    sections: Sequence[dict[str, Any]] | None = None,
) -> Deliverable:
    deliv = Deliverable(
        firm_id=scope.firm_id,
        mandate_id=mandate_id,
        job_id=job_id,
        doc_type=doc_type,
        title=title,
        status="draft",
        s3_key=s3_key,
        current_version=1,
    )
    db.add(deliv)
    await db.flush()

    if sections:
        for idx, sec in enumerate(sections):
            d_sec = DeliverableSection(
                deliverable_id=deliv.id,
                ord=sec.get("ord", idx + 1),
                section_type=sec.get("section_type", "standard_clause"),
                content=sec.get("content", ""),
                valuation_line_ids=sec.get("valuation_line_ids"),
                document_ids=sec.get("document_ids"),
            )
            db.add(d_sec)

    version_1 = DeliverableVersion(
        deliverable_id=deliv.id,
        version=1,
        s3_key=s3_key or f"deliverables/{deliv.id}/v1.docx",
        note="Initial generated draft",
    )
    db.add(version_1)
    await db.flush()
    return deliv


async def get_deliverable(
    db: AsyncSession, scope: FirmScope, deliverable_id: uuid.UUID
) -> Deliverable | None:
    stmt = (
        select(Deliverable)
        .where(Deliverable.id == deliverable_id, Deliverable.firm_id == scope.firm_id)
        .options(selectinload(Deliverable.sections), selectinload(Deliverable.versions))
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def list_deliverables(
    db: AsyncSession, scope: FirmScope, mandate_id: uuid.UUID | None = None
) -> Sequence[Deliverable]:
    stmt = select(Deliverable).where(Deliverable.firm_id == scope.firm_id)
    if mandate_id:
        stmt = stmt.where(Deliverable.mandate_id == mandate_id)
    stmt = stmt.order_by(Deliverable.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


async def get_provenance(
    db: AsyncSession, scope: FirmScope, deliverable_id: uuid.UUID
) -> dict[str, Any] | None:
    """
    Resolve full section -> figure -> comparable and section -> document provenance chain.
    """
    deliv = await get_deliverable(db, scope, deliverable_id)
    if not deliv:
        return None

    all_line_ids: list[uuid.UUID] = []
    all_doc_ids: list[uuid.UUID] = []

    for sec in deliv.sections:
        if sec.valuation_line_ids:
            all_line_ids.extend(sec.valuation_line_ids)
        if sec.document_ids:
            all_doc_ids.extend(sec.document_ids)

    line_map: dict[uuid.UUID, ValuationLine] = {}
    all_comp_ids: list[uuid.UUID] = []
    if all_line_ids:
        line_stmt = select(ValuationLine).where(ValuationLine.id.in_(all_line_ids))
        line_res = await db.execute(line_stmt)
        for line in line_res.scalars():
            line_map[line.id] = line
            if line.comparable_ids:
                all_comp_ids.extend(line.comparable_ids)

    comp_map: dict[uuid.UUID, Comparable] = {}
    if all_comp_ids:
        comp_stmt = select(Comparable).where(Comparable.id.in_(all_comp_ids))
        comp_res = await db.execute(comp_stmt)
        for comp in comp_res.scalars():
            comp_map[comp.id] = comp

    doc_map: dict[uuid.UUID, PropertyDocument] = {}
    if all_doc_ids:
        doc_stmt = select(PropertyDocument).where(PropertyDocument.id.in_(all_doc_ids))
        doc_res = await db.execute(doc_stmt)
        for doc in doc_res.scalars():
            doc_map[doc.id] = doc

    sections_payload = []
    for sec in deliv.sections:
        figures = []
        if sec.valuation_line_ids:
            for lid in sec.valuation_line_ids:
                line_row = line_map.get(lid)
                if line_row:
                    line_comps = [
                        {
                            "comparable_id": str(cid),
                            "address": comp_map[cid].address if cid in comp_map else "Unknown",
                            "sale_price": str(comp_map[cid].sale_price) if cid in comp_map else None,
                            "rate_per_unit": str(comp_map[cid].rate_per_unit) if cid in comp_map else None,
                        }
                        for cid in (line_row.comparable_ids or [])
                    ]
                    figures.append({
                        "valuation_line_id": str(line_row.id),
                        "label": line_row.label,
                        "amount": str(line_row.amount),
                        "basis": line_row.basis,
                        "source_ref": line_row.source_ref,
                        "comparables": line_comps,
                    })

        documents = []
        if sec.document_ids:
            for did in sec.document_ids:
                doc_row = doc_map.get(did)
                if doc_row:
                    documents.append({
                        "document_id": str(doc_row.id),
                        "kind": doc_row.kind,
                        "doc_date": doc_row.doc_date.isoformat() if doc_row.doc_date else None,
                        "issuing_authority": doc_row.issuing_authority,
                        "s3_key": doc_row.s3_key,
                    })

        sections_payload.append({
            "section_id": str(sec.id),
            "ord": sec.ord,
            "section_type": sec.section_type,
            "content": sec.content,
            "figures": figures,
            "documents": documents,
        })

    return {
        "deliverable_id": str(deliv.id),
        "doc_type": deliv.doc_type,
        "title": deliv.title,
        "status": deliv.status,
        "sections": sections_payload,
    }
