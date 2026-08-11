"""firms, users, jobs, properties — with PostGIS and a hand-written GiST index

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-11

Hand-review notes for this revision:
  - No monetary column exists yet; `properties` areas are NUMERIC(18,4), not
    float. `tests/test_schema_money.py` enforces this for every column added
    from here on.
  - The GiST index on `properties.geom` is written by hand below. Autogenerate
    does not emit it, and without it comparable search degrades to a sequential
    scan as soon as the table is non-trivial — silently, which is worse.
  - `properties` is in the first revision, not a later one, because S2's exit
    proof is `\\d properties` showing that index.
  - `downgrade()` drops in dependency order and is reversible. The PostGIS
    extension is deliberately *not* dropped: other schemas in the same database
    may depend on it, and dropping an extension is not a safe undo.
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Extensions first. docker/postgres/Dockerfile bakes them into the image, but
    # a managed Postgres (Render) needs them created here.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "firms",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("plan", sa.String(length=50), nullable=False),
        sa.Column("seats", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_firms"),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=True),
        sa.Column("google_sub", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("ibbi_reg_no", sa.String(length=50), nullable=True),
        sa.Column("valuer_asset_class", sa.String(length=50), nullable=True),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"], name="fk_users_firm", ondelete="CASCADE"),
        sa.UniqueConstraint("firm_id", "email", name="uq_users_firm_email"),
        sa.UniqueConstraint("google_sub", name="uq_users_google_sub"),
    )
    op.create_index("ix_users_firm_id", "users", ["firm_id"])

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("mandate_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("job_type", sa.String(length=60), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("import_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        sa.Column("doc_url", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        # Finality marker. Once set, `jobRepository` refuses any status write.
        sa.Column("terminal_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_jobs"),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"], name="fk_jobs_firm", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_jobs_user", ondelete="SET NULL"),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_firm_created", "jobs", ["firm_id", "created_at"])
    # Partial: a job without an idempotency key does not collide with another.
    op.create_index(
        "uq_jobs_idempotency_key",
        "jobs",
        ["idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    op.create_table(
        "properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("mandate_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("property_type", sa.String(length=60), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("locality", sa.String(length=200), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("state", sa.String(length=60), nullable=True),
        sa.Column("pincode", sa.String(length=10), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geography(
                geometry_type="POINT", srid=4326, spatial_index=False, from_text="ST_GeogFromText"
            ),
            nullable=True,
        ),
        sa.Column("survey_no", sa.String(length=120), nullable=True),
        sa.Column("khasra_no", sa.String(length=120), nullable=True),
        # Areas: NUMERIC, never float. A rounded area times a rate is a wrong value.
        sa.Column("land_area", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("land_area_unit", sa.String(length=20), nullable=True),
        sa.Column("built_up_area", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("carpet_area", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("floors", sa.Integer(), nullable=True),
        sa.Column("tenure", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_properties"),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"], name="fk_properties_firm", ondelete="CASCADE"),
    )
    op.create_index("ix_properties_firm_id", "properties", ["firm_id"])
    op.create_index("ix_properties_firm_city", "properties", ["firm_id", "city"])

    # ── The index autogenerate will not write for you ─────────────────────────
    # Without this, `ST_DWithin(geom, :point, :radius)` is a sequential scan over
    # every property in the database. §9 of the plan calls this out because the
    # failure mode is silent: the query still returns correct rows, just slowly,
    # and only at a table size where fixing it is disruptive.
    op.create_index("ix_properties_geom", "properties", ["geom"], postgresql_using="gist")


def downgrade() -> None:
    op.drop_index("ix_properties_geom", table_name="properties")
    op.drop_index("ix_properties_firm_city", table_name="properties")
    op.drop_index("ix_properties_firm_id", table_name="properties")
    op.drop_table("properties")

    op.drop_index("uq_jobs_idempotency_key", table_name="jobs")
    op.drop_index("ix_jobs_firm_created", table_name="jobs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_table("jobs")

    op.drop_index("ix_users_firm_id", table_name="users")
    op.drop_table("users")

    op.drop_table("firms")

    # postgis and pg_trgm are intentionally left in place — another schema in the
    # same database may depend on them, and dropping an extension is not a safe
    # undo of having created it.
