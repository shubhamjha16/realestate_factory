"""
Review notes model (S13).

Enables analysts and valuers to raise, assign, respond to, and close review notes
against deliverable sections or backing comparables. The sign-off gate prevents
deliverable signing while any note remains open.
"""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk

REVIEW_NOTE_STATUSES = ("open", "responded", "closed")


class ReviewNote(TimestampMixin, Base):
    __tablename__ = "review_notes"
    __table_args__ = (
        Index("ix_review_notes_deliv_status", "deliverable_id", "status"),
        CheckConstraint(
            "status IN ('open','responded','closed')",
            name="ck_review_notes_status",
        ),
        # An open note blocks a signature. An empty one would block it while
        # saying nothing about why.
        CheckConstraint("length(btrim(note)) > 0", name="ck_review_notes_has_note"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    firm_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("firms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    deliverable_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("deliverables.id", ondelete="CASCADE"), nullable=False
    )
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("deliverable_sections.id", ondelete="SET NULL")
    )
    comparable_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("comparables.id", ondelete="SET NULL")
    )

    author_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    note: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str | None] = mapped_column(Text)
