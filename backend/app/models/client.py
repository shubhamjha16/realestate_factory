"""Clients — who the firm is instructed by."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk

CLIENT_KINDS = ("bank", "developer", "nbfc", "fund", "individual")


class Client(TimestampMixin, Base):
    __tablename__ = "clients"
    __table_args__ = (UniqueConstraint("firm_id", "name", name="uq_clients_firm_name"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    firm_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("firms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="bank")
