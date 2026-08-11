"""
The evidence tables.

Everything here exists so that an assertion of fact in a deliverable has
something to resolve to. S8's gate reads these four tables and nothing else: a
statement about ownership, tenure, encumbrance, approvals, area or age is
supported by a row here or the render blocks.

They are in one module because they are one idea — the record behind a claim —
and splitting them across four files would obscure that the gate treats them as
a set.
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
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Money, TimestampMixin, uuid_pk

# What a document can be. `encumbrance_cert` and `title_deed` are the two the
# gate asks for most often, because they are what a title assertion rests on.
DOCUMENT_KINDS = (
    "title_deed", "mutation", "approval", "encumbrance_cert",
    "tax_receipt", "photo", "plan", "lease_deed", "share_certificate",
)

ENCUMBRANCE_KINDS = ("mortgage", "lien", "litigation", "lease", "attachment")

APPROVAL_KINDS = ("cc", "oc", "noc_fire", "noc_env", "layout", "building_plan", "rera")


class PropertyDocument(TimestampMixin, Base):
    __tablename__ = "property_documents"
    __table_args__ = (
        Index("ix_property_documents_property_kind", "property_id", "kind"),
        CheckConstraint(
            "kind IN ('title_deed','mutation','approval','encumbrance_cert',"
            "'tax_receipt','photo','plan','lease_deed','share_certificate')",
            name="ck_property_documents_kind",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    firm_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("firms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )

    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str | None] = mapped_column(String(300))
    s3_key: Mapped[str] = mapped_column(Text, nullable=False)
    doc_date: Mapped[date | None] = mapped_column(Date)
    issuing_authority: Mapped[str | None] = mapped_column(String(200))

    # Written by the OCR worker (S4's `ocr_document`, extraction lands with the
    # document pipeline). The gate does not read it; a reviewer does.
    ocr_text_s3_key: Mapped[str | None] = mapped_column(Text)

    # A document nobody has checked is a document, not evidence a valuer has
    # accepted. S13's sign-off gate is where that distinction bites.
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TitleChainEntry(TimestampMixin, Base):
    """
    One link in the chain of title.

    `ord` is the position in the chain, oldest first. A chain with a gap is not a
    chain, and the gate says so rather than letting a report call it marketable.
    """

    __tablename__ = "title_chain_entries"
    __table_args__ = (
        Index("ix_title_chain_property_ord", "property_id", "ord"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    firm_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("firms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )

    ord: Mapped[int] = mapped_column(Integer, nullable=False)
    from_party: Mapped[str] = mapped_column(String(300), nullable=False)
    to_party: Mapped[str] = mapped_column(String(300), nullable=False)
    instrument: Mapped[str] = mapped_column(String(120), nullable=False)
    registered_on: Mapped[date | None] = mapped_column(Date)
    reg_no: Mapped[str | None] = mapped_column(String(120))

    # The instrument itself. A chain entry with no document behind it is an
    # assertion, not evidence.
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("property_documents.id", ondelete="SET NULL")
    )
    document: Mapped[PropertyDocument | None] = relationship()


class Encumbrance(TimestampMixin, Base):
    __tablename__ = "encumbrances"
    __table_args__ = (
        Index("ix_encumbrances_property", "property_id"),
        CheckConstraint(
            "kind IN ('mortgage','lien','litigation','lease','attachment')",
            name="ck_encumbrances_kind",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    firm_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("firms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )

    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    holder: Mapped[str] = mapped_column(String(300), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Money)
    from_date: Mapped[date | None] = mapped_column(Date)
    to_date: Mapped[date | None] = mapped_column(Date)

    document_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("property_documents.id", ondelete="SET NULL")
    )
    document: Mapped[PropertyDocument | None] = relationship()

    @property
    def is_subsisting(self) -> bool:
        """An encumbrance with no end date has not been discharged."""
        return self.to_date is None


class Approval(TimestampMixin, Base):
    __tablename__ = "approvals"
    __table_args__ = (
        Index("ix_approvals_property_kind", "property_id", "kind"),
        CheckConstraint(
            "kind IN ('cc','oc','noc_fire','noc_env','layout','building_plan','rera')",
            name="ck_approvals_kind",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    firm_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("firms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )

    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    authority: Mapped[str] = mapped_column(String(200), nullable=False)
    ref_no: Mapped[str | None] = mapped_column(String(120))
    issued_on: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)

    document_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("property_documents.id", ondelete="SET NULL")
    )
    document: Mapped[PropertyDocument | None] = relationship()

    def is_current(self, as_of: date) -> bool:
        return self.valid_until is None or self.valid_until >= as_of
