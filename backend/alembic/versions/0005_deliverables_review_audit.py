"""deliverables and their provenance (S12), review notes and the audit trail (S13)

Revision ID: 0005_deliverables_review_audit
Revises: 0004_evidence_valuations
Create Date: 2026-08-11

Why this revision exists late
─────────────────────────────
S12 and S13 shipped their models, repositories, routers and tests without a
migration. `Base.metadata` therefore declared five tables that nothing created,
so `alembic upgrade head` produced a database in which the provenance endpoint
and the whole review and sign-off path fail on first query. It survived because
the live-database tests for both sprints skip without `TEST_DATABASE_URL`, and
the CI database job did not run them. Both of those are fixed alongside this.

Hand-review checklist for this revision:
  - No monetary column here. Deliverables carry documents and text; every figure
    they render lives in `valuation_lines`, which 0004 created as NUMERIC(18,2).
    `deliverables.current_version` is an integer counter and is listed in
    `ALLOWED_NON_MONEY` in `scripts/check_money_columns.py` because "current"
    contains "rent".
  - No geography column, so no GiST index. `properties.geom` and
    `comparables.geom` keep the ones hand-written in 0001 and 0003.
  - `firm_id` is NOT NULL on `deliverables`, `review_notes` and `audit_events` —
    the three tenanted tables here. CI asserts that property against the live
    schema for every table that has the column, because a row belonging to no
    firm is invisible to every tenant and therefore unauditable.
    `deliverable_versions` and `deliverable_sections` deliberately do not carry
    one: they are reached only through their parent deliverable and cascade with
    it, so a second copy of the firm would be a second thing to keep in step.
  - A `signed` deliverable must carry a signer and a timestamp, enforced by CHECK
    rather than left to the application — the same rule 0004 applies to a signed
    valuation, and for the same reason: a signed record with no signer cannot be
    relied upon, and there is no legitimate way to create one.
  - The rule that a deliverable cannot be signed while a review note is open is
    deliberately **not** a CHECK. It is a cross-row invariant, and enforcing it in
    the sign-off gate lets the refusal name the note that is blocking.
  - `valuation_line_ids` and `document_ids` on a section are arrays rather than
    join tables. They are read as a set on one code path — assembling a
    provenance response — and never joined against, so a join table would add two
    tables and a migration for no query anybody writes.
  - No foreign key from those arrays: PostgreSQL cannot enforce referential
    integrity on array elements. The provenance repository resolves them with an
    IN query and simply omits an id it cannot find, so a deleted comparable
    degrades the trail rather than breaking the page.
  - `audit_events` has no updated_at and no delete path by design. An audit row
    that can be edited is not an audit row.
  - `downgrade()` drops in dependency order: review notes reference sections,
    sections and versions reference deliverables.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005_deliverables_review_audit"
down_revision: str | None = "0004_evidence_valuations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── S12: the deliverable, its versions, and its sections ──────────────────
    op.create_table(
        "deliverables",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mandate_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("doc_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("s3_key", sa.String(length=500), nullable=True),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_deliverables"),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"], name="fk_deliverables_firm", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["mandate_id"], ["mandates.id"], name="fk_deliverables_mandate", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], name="fk_deliverables_job", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["reviewed_by"], ["users.id"], name="fk_deliverables_reviewer", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["signed_by"], ["users.id"], name="fk_deliverables_signer", ondelete="SET NULL"
        ),
        sa.CheckConstraint(
            "status IN ('draft','in_review','final','signed')",
            name="ck_deliverables_status",
        ),
        # Same rule 0004 applies to a signed valuation. A signed deliverable with
        # no signer and no time is a record nobody can rely on, and there is no
        # legitimate way to create one.
        sa.CheckConstraint(
            "status <> 'signed' OR (signed_by IS NOT NULL AND signed_at IS NOT NULL)",
            name="ck_deliverables_signed_has_signer",
        ),
    )
    op.create_index("ix_deliverables_firm_id", "deliverables", ["firm_id"])
    op.create_index("ix_deliverables_mandate_firm", "deliverables", ["mandate_id", "firm_id"])

    op.create_table(
        "deliverable_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deliverable_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("s3_key", sa.String(length=500), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_deliverable_versions"),
        sa.ForeignKeyConstraint(
            ["deliverable_id"], ["deliverables.id"], name="fk_version_deliverable", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_version_author", ondelete="SET NULL"),
        # A version number appears once per deliverable. Without this, two writers
        # racing to publish both produce "version 3" and the history stops being
        # a history.
        sa.UniqueConstraint("deliverable_id", "version", name="uq_version_per_deliverable"),
    )
    op.create_index("ix_deliverable_versions_deliverable_id", "deliverable_versions", ["deliverable_id"])

    op.create_table(
        "deliverable_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deliverable_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ord", sa.Integer(), nullable=False),
        sa.Column("section_type", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        # The provenance chain, S12's whole point: every figure in this section
        # traces to a valuation line, every factual assertion to a document.
        sa.Column(
            "valuation_line_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True
        ),
        sa.Column("document_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_deliverable_sections"),
        sa.ForeignKeyConstraint(
            ["deliverable_id"], ["deliverables.id"], name="fk_section_deliverable", ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_deliverable_sections_deliv_ord", "deliverable_sections", ["deliverable_id", "ord"]
    )

    # ── S13: review notes ─────────────────────────────────────────────────────
    op.create_table(
        "review_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deliverable_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("comparable_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_review_notes"),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"], name="fk_notes_firm", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["deliverable_id"], ["deliverables.id"], name="fk_notes_deliverable", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["section_id"], ["deliverable_sections.id"], name="fk_notes_section", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["comparable_id"], ["comparables.id"], name="fk_notes_comparable", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], name="fk_notes_author", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["assigned_to"], ["users.id"], name="fk_notes_assignee", ondelete="SET NULL"
        ),
        sa.CheckConstraint(
            "status IN ('open','responded','closed')",
            name="ck_review_notes_status",
        ),
        # A note is the mechanism the sign-off gate reads, so an empty one would
        # block a signature while saying nothing about why.
        sa.CheckConstraint("length(btrim(note)) > 0", name="ck_review_notes_has_note"),
    )
    op.create_index("ix_review_notes_firm_id", "review_notes", ["firm_id"])
    op.create_index("ix_review_notes_deliv_status", "review_notes", ["deliverable_id", "status"])

    # ── S12/S13: the audit trail ──────────────────────────────────────────────
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource", sa.String(length=100), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"], name="fk_audit_firm", ondelete="CASCADE"),
        # The actor survives the user being deleted. "Who exported this" answered
        # with a null is a worse answer than a stale one, but a foreign key that
        # cascaded would delete the evidence along with the account.
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], name="fk_audit_actor", ondelete="SET NULL"),
    )
    op.create_index("ix_audit_events_firm_id", "audit_events", ["firm_id"])
    op.create_index("ix_audit_events_firm_action", "audit_events", ["firm_id", "action"])
    op.create_index("ix_audit_events_resource", "audit_events", ["resource", "resource_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_resource", table_name="audit_events")
    op.drop_index("ix_audit_events_firm_action", table_name="audit_events")
    op.drop_index("ix_audit_events_firm_id", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index("ix_review_notes_deliv_status", table_name="review_notes")
    op.drop_index("ix_review_notes_firm_id", table_name="review_notes")
    op.drop_table("review_notes")

    op.drop_index("ix_deliverable_sections_deliv_ord", table_name="deliverable_sections")
    op.drop_table("deliverable_sections")

    op.drop_index("ix_deliverable_versions_deliverable_id", table_name="deliverable_versions")
    op.drop_table("deliverable_versions")

    op.drop_index("ix_deliverables_mandate_firm", table_name="deliverables")
    op.drop_index("ix_deliverables_firm_id", table_name="deliverables")
    op.drop_table("deliverables")
