"""Firms — the tenancy boundary. Every scoped row carries `firm_id`."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.user import User


class Firm(TimestampMixin, Base):
    __tablename__ = "firms"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="starter")
    seats: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    users: Mapped[list[User]] = relationship(back_populates="firm")  # noqa: F821
