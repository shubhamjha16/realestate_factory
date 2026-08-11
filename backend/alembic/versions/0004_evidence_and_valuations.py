"""evidence tables (S8) and valuations with approaches and lines (S9)

Revision ID: 0004_evidence_valuations
Revises: 0003_comparables
Create Date: 2026-08-11

Hand-review checklist for this revision:
  - Monetary columns are NUMERIC(18,2): `encumbrances.amount`,
    `valuations.concluded_value` and its range, `valuation_approaches
    .indicated_value`, `valuation_lines.amount`. Checked by
    `scripts/check_money_columns.py`.
  - No geography column here, so no GiST index is needed. `properties.geom` and
    `comparables.geom` keep the ones hand-written in 0001 and 0003.
  - `rationale` on `valuation_approaches` is NOT NULL with a non-blank CHECK,
    matching `comparable_adjustments`. A weight is a judgement; a judgement with
    no reason cannot be reviewed.
  - A `signed` valuation must carry a signer and a timestamp — enforced by CHECK
    rather than left to the application, because a signed record with no signer
    cannot be relied upon and there is no legitimate way to create one.
  - The weights-sum-to-1 rule is deliberately **not** a CHECK: it is a cross-row
    invariant, and enforcing it in `reconcile.py` lets the error say which
    weights and by how much.
  - `downgrade()` drops in dependency order.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_evidence_valuations"
down_revision: str | None = "0003_comparables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── S8: what an assertion of fact resolves to ─────────────────────────────
    op.create_table(
        "property_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=True),
        sa.Column("s3_key", sa.Text(), nullable=False),
        sa.Column("doc_date", sa.Date(), nullable=True),
        sa.Column("issuing_authority", sa.String(length=200), nullable=True),
        sa.Column("ocr_text_s3_key", sa.Text(), nullable=True),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_property_documents"),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"], name="fk_documents_firm", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], name="fk_documents_property", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["verified_by"], ["users.id"], name="fk_documents_verifier", ondelete="SET NULL"),
        sa.CheckConstraint(
            "kind IN ('title_deed','mutation','approval','encumbrance_cert',"
            "'tax_receipt','photo','plan','lease_deed','share_certificate')",
            name="ck_property_documents_kind",
        ),
    )
    op.create_index("ix_property_documents_firm_id", "property_documents", ["firm_id"])
    op.create_index("ix_property_documents_property_kind", "property_documents", ["property_id", "kind"])

    op.create_table(
        "title_chain_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ord", sa.Integer(), nullable=False),
        sa.Column("from_party", sa.String(length=300), nullable=False),
        sa.Column("to_party", sa.String(length=300), nullable=False),
        sa.Column("instrument", sa.String(length=120), nullable=False),
        sa.Column("registered_on", sa.Date(), nullable=True),
        sa.Column("reg_no", sa.String(length=120), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_title_chain_entries"),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"], name="fk_title_chain_firm", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], name="fk_title_chain_property", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["property_documents.id"], name="fk_title_chain_document", ondelete="SET NULL"),
    )
    op.create_index("ix_title_chain_entries_firm_id", "title_chain_entries", ["firm_id"])
    op.create_index("ix_title_chain_property_ord", "title_chain_entries", ["property_id", "ord"])

    op.create_table(
        "encumbrances",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("holder", sa.String(length=300), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("from_date", sa.Date(), nullable=True),
        sa.Column("to_date", sa.Date(), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_encumbrances"),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"], name="fk_encumbrances_firm", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], name="fk_encumbrances_property", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["property_documents.id"], name="fk_encumbrances_document", ondelete="SET NULL"),
        sa.CheckConstraint(
            "kind IN ('mortgage','lien','litigation','lease','attachment')",
            name="ck_encumbrances_kind",
        ),
    )
    op.create_index("ix_encumbrances_firm_id", "encumbrances", ["firm_id"])
    op.create_index("ix_encumbrances_property", "encumbrances", ["property_id"])

    op.create_table(
        "approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("authority", sa.String(length=200), nullable=False),
        sa.Column("ref_no", sa.String(length=120), nullable=True),
        sa.Column("issued_on", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_approvals"),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"], name="fk_approvals_firm", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], name="fk_approvals_property", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["property_documents.id"], name="fk_approvals_document", ondelete="SET NULL"),
        sa.CheckConstraint(
            "kind IN ('cc','oc','noc_fire','noc_env','layout','building_plan','rera')",
            name="ck_approvals_kind",
        ),
    )
    op.create_index("ix_approvals_firm_id", "approvals", ["firm_id"])
    op.create_index("ix_approvals_property_kind", "approvals", ["property_id", "kind"])

    # ── S9: valuations, approaches, lines ─────────────────────────────────────
    op.create_table(
        "valuations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mandate_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("valuation_date", sa.Date(), nullable=False),
        sa.Column("basis", sa.String(length=20), nullable=False),
        sa.Column("premise", sa.String(length=30), nullable=False),
        sa.Column("concluded_value", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("value_range_low", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("value_range_high", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("valuer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_valuations"),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"], name="fk_valuations_firm", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], name="fk_valuations_property", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mandate_id"], ["mandates.id"], name="fk_valuations_mandate", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["valuer_id"], ["users.id"], name="fk_valuations_valuer", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["signed_by"], ["users.id"], name="fk_valuations_signer", ondelete="SET NULL"),
        sa.CheckConstraint("basis IN ('market','fair','liquidation','distress','insurable')", name="ck_valuations_basis"),
        sa.CheckConstraint("premise IN ('existing_use','highest_best_use')", name="ck_valuations_premise"),
        sa.CheckConstraint("status IN ('draft','in_review','final','signed')", name="ck_valuations_status"),
        sa.CheckConstraint(
            "(status <> 'signed') OR (signed_by IS NOT NULL AND signed_at IS NOT NULL)",
            name="ck_valuations_signed_has_signer",
        ),
        sa.CheckConstraint(
            "value_range_low <= concluded_value AND concluded_value <= value_range_high",
            name="ck_valuations_conclusion_within_range",
        ),
    )
    op.create_index("ix_valuations_firm_id", "valuations", ["firm_id"])
    op.create_index("ix_valuations_property_date", "valuations", ["property_id", "valuation_date"])

    op.create_table(
        "valuation_approaches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("valuation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("indicated_value", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("weight", sa.Numeric(precision=9, scale=4), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("inputs", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_valuation_approaches"),
        sa.ForeignKeyConstraint(["valuation_id"], ["valuations.id"], name="fk_approach_valuation", ondelete="CASCADE"),
        sa.UniqueConstraint("valuation_id", "method", name="uq_approach_valuation_method"),
        sa.CheckConstraint("method IN ('sales','income','cost')", name="ck_approach_method"),
        sa.CheckConstraint("weight >= 0 AND weight <= 1", name="ck_approach_weight_range"),
        sa.CheckConstraint("length(btrim(rationale)) > 0", name="ck_approach_has_rationale"),
    )
    op.create_index("ix_valuation_approaches_valuation_id", "valuation_approaches", ["valuation_id"])

    op.create_table(
        "valuation_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("valuation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approach_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ord", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=300), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("basis", sa.String(length=120), nullable=True),
        sa.Column("source_ref", postgresql.JSONB(), nullable=True),
        sa.Column("comparable_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_valuation_lines"),
        sa.ForeignKeyConstraint(["valuation_id"], ["valuations.id"], name="fk_line_valuation", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["approach_id"], ["valuation_approaches.id"], name="fk_line_approach", ondelete="CASCADE"),
    )
    op.create_index("ix_valuation_lines_valuation_ord", "valuation_lines", ["valuation_id", "ord"])


def downgrade() -> None:
    op.drop_index("ix_valuation_lines_valuation_ord", table_name="valuation_lines")
    op.drop_table("valuation_lines")
    op.drop_index("ix_valuation_approaches_valuation_id", table_name="valuation_approaches")
    op.drop_table("valuation_approaches")
    op.drop_index("ix_valuations_property_date", table_name="valuations")
    op.drop_index("ix_valuations_firm_id", table_name="valuations")
    op.drop_table("valuations")

    for table in ("approvals", "encumbrances", "title_chain_entries"):
        op.drop_table(table)
    op.drop_index("ix_property_documents_property_kind", table_name="property_documents")
    op.drop_index("ix_property_documents_firm_id", table_name="property_documents")
    op.drop_table("property_documents")
