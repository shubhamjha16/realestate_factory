"""
Valuations, their approaches, and the lines a figure traces to.

`valuation_lines` is what S11 and S12 are built on: **no number reaches rendered
output unless it came from a line here.** The table exists now so that the
approaches written in S9 record their figures somewhere a provenance chain can
reach, rather than being recomputed at render time from something a model wrote.

`valuation_approaches.weight` has a CHECK for its range but not for its sum —
that is a cross-row invariant, enforced in `services/valuation/reconcile.py`
where the error can say which weights and by how much.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Money, Percent, TimestampMixin, uuid_pk

VALUATION_BASES = ("market", "fair", "liquidation", "distress", "insurable")
VALUATION_PREMISES = ("existing_use", "highest_best_use")
VALUATION_STATUSES = ("draft", "in_review", "final", "signed")
APPROACH_METHODS = ("sales", "income", "cost")


class Valuation(TimestampMixin, Base):
    __tablename__ = "valuations"
    __table_args__ = (
        Index("ix_valuations_property_date", "property_id", "valuation_date"),
        CheckConstraint(
            "basis IN ('market','fair','liquidation','distress','insurable')",
            name="ck_valuations_basis",
        ),
        CheckConstraint(
            "premise IN ('existing_use','highest_best_use')", name="ck_valuations_premise"
        ),
        CheckConstraint(
            "status IN ('draft','in_review','final','signed')", name="ck_valuations_status"
        ),
        # A signed valuation without a signer is a record that cannot be relied
        # on. S13 enforces who may sign; the schema enforces that someone did.
        CheckConstraint(
            "(status <> 'signed') OR (signed_by IS NOT NULL AND signed_at IS NOT NULL)",
            name="ck_valuations_signed_has_signer",
        ),
        CheckConstraint(
            "value_range_low <= concluded_value AND concluded_value <= value_range_high",
            name="ck_valuations_conclusion_within_range",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    firm_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("firms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    mandate_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("mandates.id", ondelete="SET NULL")
    )

    valuation_date: Mapped[date] = mapped_column(Date, nullable=False)
    basis: Mapped[str] = mapped_column(String(20), nullable=False)
    premise: Mapped[str] = mapped_column(String(30), nullable=False, default="existing_use")

    concluded_value: Mapped[Decimal] = mapped_column(Money, nullable=False)
    value_range_low: Mapped[Decimal] = mapped_column(Money, nullable=False)
    value_range_high: Mapped[Decimal] = mapped_column(Money, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    valuer_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    signed_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    approaches: Mapped[list[ValuationApproach]] = relationship(
        back_populates="valuation", cascade="all, delete-orphan"
    )
    lines: Mapped[list[ValuationLine]] = relationship(
        back_populates="valuation", cascade="all, delete-orphan"
    )


class ValuationApproach(TimestampMixin, Base):
    __tablename__ = "valuation_approaches"
    __table_args__ = (
        UniqueConstraint("valuation_id", "method", name="uq_approach_valuation_method"),
        CheckConstraint("method IN ('sales','income','cost')", name="ck_approach_method"),
        CheckConstraint("weight >= 0 AND weight <= 1", name="ck_approach_weight_range"),
        # A weight is a judgement about which evidence is better. Judgements
        # carry reasons, and the schema will not hold one without.
        CheckConstraint("length(btrim(rationale)) > 0", name="ck_approach_has_rationale"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    valuation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("valuations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    method: Mapped[str] = mapped_column(String(10), nullable=False)
    indicated_value: Mapped[Decimal] = mapped_column(Money, nullable=False)
    weight: Mapped[Decimal] = mapped_column(Percent, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    # The workings: the operating statement, the depreciation split, the grid.
    inputs: Mapped[dict | None] = mapped_column(JSONB)

    valuation: Mapped[Valuation] = relationship(back_populates="approaches")


class ValuationLine(TimestampMixin, Base):
    """
    One figure, with where it came from.

    S11 makes this load-bearing: a number in rendered output that does not match
    a line here blocks the render. S12 turns `source_ref` into a chain a reviewer
    can click through — figure to adjusted comparable to source sheet.
    """

    __tablename__ = "valuation_lines"
    __table_args__ = (
        Index("ix_valuation_lines_valuation_ord", "valuation_id", "ord"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    valuation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("valuations.id", ondelete="CASCADE"),
        nullable=False,
    )
    approach_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("valuation_approaches.id", ondelete="CASCADE")
    )

    ord: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(300), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    basis: Mapped[str | None] = mapped_column(String(120))

    # The provenance chain: which comparables, which documents, which import.
    source_ref: Mapped[dict | None] = mapped_column(JSONB)
    comparable_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(PGUUID(as_uuid=True)))

    valuation: Mapped[Valuation] = relationship(back_populates="lines")
