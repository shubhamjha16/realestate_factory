"""
Users.

`ibbi_reg_no` and `valuer_asset_class` sit here rather than in a separate table
because the sign-off gate (S13) reads them on every attempt to sign: a valuation
may only reach `signed` by a user whose registration covers that asset class.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.firm import Firm

USER_ROLES = ("partner", "valuer", "analyst", "readonly", "client")


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("firm_id", "email", name="uq_users_firm_email"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    firm_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("firms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255))
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="analyst")

    ibbi_reg_no: Mapped[str | None] = mapped_column(String(50))
    valuer_asset_class: Mapped[str | None] = mapped_column(String(50))
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    firm: Mapped[Firm] = relationship(back_populates="users")  # noqa: F821
