"""clients, mandates, MFA columns, and firm_id made NOT NULL

Revision ID: 0002_tenancy
Revises: 0001_initial
Create Date: 2026-08-11

Hand-review notes for this revision:
  - No monetary column. `scripts/check_money_columns.py` runs over this file.
  - No geography column, so no GiST index is needed here. `properties.geom`
    keeps the one hand-written in 0001.
  - `jobs.firm_id` and `properties.firm_id` become NOT NULL. Every scoped read
    filters on them, and a NULL is a row that belongs to no firm — invisible to
    every tenant and therefore unauditable.
  - **This revision refuses to run if pre-tenancy rows exist** rather than
    guessing which firm they belong to or deleting them. See `_require_no_orphans`.
  - `downgrade()` restores nullability and drops the new tables in dependency
    order. It does not attempt to un-assign firms, because it cannot know which
    assignments were made by this migration and which by ordinary use.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_tenancy"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _require_no_orphans() -> None:
    """
    Refuse to make `firm_id` NOT NULL while rows exist that have no firm.

    Those rows can only come from a deployment that ran before tenancy existed.
    Assigning them to an arbitrary firm would hand one tenant another's data;
    deleting them would destroy records this migration has no mandate over. So
    it stops and tells the operator, who is the only one who knows which it is.
    """
    conn = op.get_bind()
    for table in ("jobs", "properties"):
        count = conn.execute(
            sa.text(f"SELECT count(*) FROM {table} WHERE firm_id IS NULL")  # noqa: S608
        ).scalar_one()
        if count:
            raise RuntimeError(
                f"{count} row(s) in {table!r} have no firm_id. These predate tenancy "
                f"(S5) and this migration will not guess who they belong to.\n"
                f"Assign them to a firm, or — if this is a pre-production database "
                f"whose contents are disposable — delete them:\n"
                f"    DELETE FROM {table} WHERE firm_id IS NULL;\n"
                f"then run `alembic upgrade head` again."
            )


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_clients"),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"], name="fk_clients_firm", ondelete="CASCADE"),
        sa.UniqueConstraint("firm_id", "name", name="uq_clients_firm_name"),
    )
    op.create_index("ix_clients_firm_id", "clients", ["firm_id"])

    op.create_table(
        "mandates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        # Drives the basis of value and, from S9, which approaches are mandatory.
        sa.Column("purpose", sa.String(length=30), nullable=False),
        sa.Column("instructed_on", sa.Date(), nullable=True),
        sa.Column("due_on", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("valuer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_mandates"),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"], name="fk_mandates_firm", ondelete="CASCADE"),
        # RESTRICT, not CASCADE: deleting a client must not silently take its
        # mandates and everything hanging off them.
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name="fk_mandates_client", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["valuer_id"], ["users.id"], name="fk_mandates_valuer", ondelete="SET NULL"),
    )
    op.create_index("ix_mandates_firm_id", "mandates", ["firm_id"])
    op.create_index("ix_mandates_client_id", "mandates", ["client_id"])

    # ── users: MFA and account state ──────────────────────────────────────────
    op.add_column("users", sa.Column("totp_secret", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))

    # ── tenancy becomes mandatory ─────────────────────────────────────────────
    _require_no_orphans()
    op.alter_column("jobs", "firm_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.alter_column("properties", "firm_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)

    # The FK 0001 deferred until mandates existed.
    op.create_foreign_key(
        "fk_properties_mandate", "properties", "mandates", ["mandate_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_jobs_mandate", "jobs", "mandates", ["mandate_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_jobs_mandate_id", "jobs", ["mandate_id"])
    op.create_index("ix_properties_mandate_id", "properties", ["mandate_id"])


def downgrade() -> None:
    op.drop_index("ix_properties_mandate_id", table_name="properties")
    op.drop_index("ix_jobs_mandate_id", table_name="jobs")
    op.drop_constraint("fk_jobs_mandate", "jobs", type_="foreignkey")
    op.drop_constraint("fk_properties_mandate", "properties", type_="foreignkey")

    op.alter_column("properties", "firm_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.alter_column("jobs", "firm_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)

    op.drop_column("users", "last_login_at")
    op.drop_column("users", "is_active")
    op.drop_column("users", "totp_secret")

    op.drop_index("ix_mandates_client_id", table_name="mandates")
    op.drop_index("ix_mandates_firm_id", table_name="mandates")
    op.drop_table("mandates")

    op.drop_index("ix_clients_firm_id", table_name="clients")
    op.drop_table("clients")
