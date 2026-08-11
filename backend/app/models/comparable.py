"""
Comparables and their adjustments.

`comparable_adjustments` **is the valuation's defensibility**. It is the table a
reviewer, a bank or a tribunal asks to see, and the reason `rationale` is NOT
NULL: a percentage nobody explained cannot be reviewed, so the schema refuses to
hold one.

Money is `NUMERIC(18,2)`. These are the first monetary columns in the schema, so
`scripts/check_money_columns.py` starts earning its place here.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from geoalchemy2 import Geography
from sqlalchemy import (
    Boolean,
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
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Area, Base, Money, Percent, TimestampMixin, uuid_pk

# Mirrors ADJUSTMENT_ORDER in services/valuation/adjust.py. The order matters:
# adjustments compound, so applying them in a different order than the report
# describes produces a different number than the report explains.
ADJUSTMENT_FACTORS = (
    "time", "location", "tenure", "size", "age",
    "floor", "frontage", "view", "condition", "distress",
)


class Comparable(TimestampMixin, Base):
    __tablename__ = "comparables"
    __table_args__ = (
        Index("ix_comparables_geom", "geom", postgresql_using="gist"),
        Index("ix_comparables_property_date", "property_id", "sale_date"),
        CheckConstraint("area > 0", name="ck_comparables_area_positive"),
        CheckConstraint("sale_price > 0", name="ck_comparables_price_positive"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    firm_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("firms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )

    source: Mapped[str | None] = mapped_column(String(120))
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    geom: Mapped[str | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False)
    )

    sale_date: Mapped[date] = mapped_column(Date, nullable=False)
    sale_price: Mapped[Decimal] = mapped_column(Money, nullable=False)
    area: Mapped[Decimal] = mapped_column(Area, nullable=False)
    area_unit: Mapped[str] = mapped_column(String(20), nullable=False, default="sqft")
    rate_per_unit: Mapped[Decimal] = mapped_column(Money, nullable=False)

    property_type: Mapped[str | None] = mapped_column(String(60))
    age_years: Mapped[int | None] = mapped_column(Integer)
    floor: Mapped[int | None] = mapped_column(Integer)
    distance_m: Mapped[Decimal | None] = mapped_column(Area)
    tenure: Mapped[str | None] = mapped_column(String(20))

    # A comparable nobody has checked is evidence nobody has checked. S7 does not
    # block on it; S13's sign-off gate is where an unverified comparable behind a
    # signed figure becomes a problem.
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_reason: Mapped[str | None] = mapped_column(Text)

    note: Mapped[str | None] = mapped_column(Text)

    adjustments: Mapped[list[ComparableAdjustment]] = relationship(
        back_populates="comparable", cascade="all, delete-orphan"
    )


class ComparableAdjustment(TimestampMixin, Base):
    """
    One line of the grid.

    `pct` is signed and expressed against the comparable: +5 means the comparable
    is inferior to the subject on this factor, so its rate is adjusted upward to
    stand in for it.
    """

    __tablename__ = "comparable_adjustments"
    __table_args__ = (
        # One line per factor. Two `floor` adjustments on the same comparable
        # would be a grid that does not add up to what it shows.
        UniqueConstraint("comparable_id", "factor", name="uq_adjustment_comparable_factor"),
        CheckConstraint(
            "factor IN ('time','location','tenure','size','age','floor','frontage',"
            "'view','condition','distress')",
            name="ck_adjustment_factor",
        ),
        # Beyond ±50% the property is not a comparable, it is a different asset.
        CheckConstraint("pct >= -50 AND pct <= 50", name="ck_adjustment_within_bounds"),
        # The rule the whole table exists for.
        CheckConstraint("length(btrim(rationale)) > 0", name="ck_adjustment_has_rationale"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    comparable_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("comparables.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    factor: Mapped[str] = mapped_column(String(20), nullable=False)
    pct: Mapped[Decimal] = mapped_column(Percent, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)

    applied_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    comparable: Mapped[Comparable] = relationship(back_populates="adjustments")
