"""
Deliverables, deliverable versions, and deliverable sections.

`deliverable_sections` links figures to `valuation_line_ids` and legal/factual assertions
to `document_ids` — enabling full provenance tracing from report text to source sheets
and registered title documents (S12).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, uuid_pk

DELIVERABLE_STATUSES = ("draft", "in_review", "final", "signed")


class Deliverable(TimestampMixin, Base):
    __tablename__ = "deliverables"
    __table_args__ = (
        Index("ix_deliverables_mandate_firm", "mandate_id", "firm_id"),
        CheckConstraint(
            "status IN ('draft','in_review','final','signed')",
            name="ck_deliverables_status",
        ),
        # The same rule a signed valuation carries: a signed record with no
        # signer and no time is one nobody can rely on, and there is no
        # legitimate way to create one. Enforced here rather than in the
        # sign-off gate because there are several writers and a rule held in one
        # caller is a rule the next caller does not know about.
        CheckConstraint(
            "status <> 'signed' OR (signed_by IS NOT NULL AND signed_at IS NOT NULL)",
            name="ck_deliverables_signed_has_signer",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    firm_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("firms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mandate_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("mandates.id", ondelete="SET NULL")
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL")
    )

    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    signed_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    s3_key: Mapped[str | None] = mapped_column(String(500))
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    versions: Mapped[list[DeliverableVersion]] = relationship(
        back_populates="deliverable", cascade="all, delete-orphan"
    )
    sections: Mapped[list[DeliverableSection]] = relationship(
        back_populates="deliverable", cascade="all, delete-orphan", order_by="DeliverableSection.ord"
    )


class DeliverableVersion(TimestampMixin, Base):
    __tablename__ = "deliverable_versions"
    __table_args__ = (
        # Two writers racing to publish both produce "version 3", and the
        # history stops being a history.
        UniqueConstraint("deliverable_id", "version", name="uq_version_per_deliverable"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    deliverable_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("deliverables.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    note: Mapped[str | None] = mapped_column(Text)

    deliverable: Mapped[Deliverable] = relationship(back_populates="versions")


class DeliverableSection(TimestampMixin, Base):
    __tablename__ = "deliverable_sections"
    __table_args__ = (
        Index("ix_deliverable_sections_deliv_ord", "deliverable_id", "ord"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    deliverable_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("deliverables.id", ondelete="CASCADE"), nullable=False
    )
    ord: Mapped[int] = mapped_column(Integer, nullable=False)
    section_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Section -> figure provenance (S12)
    valuation_line_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(PGUUID(as_uuid=True)))
    # Section -> legal/document evidence (S12)
    document_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(PGUUID(as_uuid=True)))

    deliverable: Mapped[Deliverable] = relationship(back_populates="sections")
