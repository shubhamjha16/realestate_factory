"""comparables and comparable_adjustments — the first monetary columns

Revision ID: 0003_comparables
Revises: 0002_tenancy
Create Date: 2026-08-11

Hand-review checklist for this revision:
  - `sale_price` and `rate_per_unit` are NUMERIC(18,2). These are the first
    monetary columns in the schema, so `scripts/check_money_columns.py` starts
    checking real columns here rather than only its synthetic fixtures.
  - `comparables.geom` is a geography column, so it gets a **hand-written GiST
    index**. Autogenerate does not emit it, and without it the "sales within
    2 km" query that comparable search is built on degrades to a sequential scan.
  - `rationale` is NOT NULL with a non-blank CHECK. This table is the
    valuation's defensibility; a percentage nobody explained cannot be reviewed,
    so the schema refuses to hold one.
  - `downgrade()` drops both tables in dependency order.
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_comparables"
down_revision: str | None = "0002_tenancy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "comparables",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column(
            "geom",
            geoalchemy2.types.Geography(
                geometry_type="POINT", srid=4326, spatial_index=False, from_text="ST_GeogFromText"
            ),
            nullable=True,
        ),
        sa.Column("sale_date", sa.Date(), nullable=False),
        # Money: NUMERIC(18,2). Never float.
        sa.Column("sale_price", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("area", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("area_unit", sa.String(length=20), nullable=False),
        sa.Column("rate_per_unit", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("property_type", sa.String(length=60), nullable=True),
        sa.Column("age_years", sa.Integer(), nullable=True),
        sa.Column("floor", sa.Integer(), nullable=True),
        sa.Column("distance_m", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("tenure", sa.String(length=20), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_reason", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_comparables"),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"], name="fk_comparables_firm", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], name="fk_comparables_property", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["verified_by"], ["users.id"], name="fk_comparables_verifier", ondelete="SET NULL"),
        sa.CheckConstraint("area > 0", name="ck_comparables_area_positive"),
        sa.CheckConstraint("sale_price > 0", name="ck_comparables_price_positive"),
    )
    op.create_index("ix_comparables_firm_id", "comparables", ["firm_id"])
    op.create_index("ix_comparables_property_date", "comparables", ["property_id", "sale_date"])

    # Hand-written. Autogenerate does not emit GiST on a geography column, and
    # comparable search is a spatial query before it is anything else.
    op.create_index("ix_comparables_geom", "comparables", ["geom"], postgresql_using="gist")

    op.create_table(
        "comparable_adjustments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comparable_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("factor", sa.String(length=20), nullable=False),
        sa.Column("pct", sa.Numeric(precision=9, scale=4), nullable=False),
        # The rule this whole table exists for.
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("applied_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_comparable_adjustments"),
        sa.ForeignKeyConstraint(
            ["comparable_id"], ["comparables.id"],
            name="fk_adjustment_comparable", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["applied_by"], ["users.id"], name="fk_adjustment_user", ondelete="SET NULL"
        ),
        sa.UniqueConstraint("comparable_id", "factor", name="uq_adjustment_comparable_factor"),
        sa.CheckConstraint(
            "factor IN ('time','location','tenure','size','age','floor','frontage',"
            "'view','condition','distress')",
            name="ck_adjustment_factor",
        ),
        sa.CheckConstraint("pct >= -50 AND pct <= 50", name="ck_adjustment_within_bounds"),
        sa.CheckConstraint("length(btrim(rationale)) > 0", name="ck_adjustment_has_rationale"),
    )
    op.create_index("ix_comparable_adjustments_comparable_id", "comparable_adjustments", ["comparable_id"])


def downgrade() -> None:
    op.drop_index("ix_comparable_adjustments_comparable_id", table_name="comparable_adjustments")
    op.drop_table("comparable_adjustments")

    op.drop_index("ix_comparables_geom", table_name="comparables")
    op.drop_index("ix_comparables_property_date", table_name="comparables")
    op.drop_index("ix_comparables_firm_id", table_name="comparables")
    op.drop_table("comparables")
