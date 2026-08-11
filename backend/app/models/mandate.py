"""
Mandates — an instruction from a client, and the unit everything else hangs off.

`purpose` is not a label. It drives the basis of value the report must be
prepared on and, from S9, which approaches are mandatory: a valuation instructed
for IBC proceedings cannot be concluded the way one instructed for a loan can.
Recording it at instruction time is what makes that enforceable later.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk

MANDATE_KINDS = ("valuation", "due_diligence", "rera", "transaction", "portfolio")
MANDATE_PURPOSES = ("loan", "ibc", "dispute", "financial_reporting", "internal")
MANDATE_STATUSES = ("open", "in_progress", "delivered", "closed")

# §11.1, settled: this platform is built for IBBI-registered valuation (IBC and
# Companies Act) and bank panel valuation. Both require a registered signer, so
# these purposes carry a registration requirement through to S13's sign-off gate.
PURPOSES_REQUIRING_REGISTERED_VALUER = frozenset({"loan", "ibc", "dispute", "financial_reporting"})


class Mandate(TimestampMixin, Base):
    __tablename__ = "mandates"

    id: Mapped[uuid.UUID] = uuid_pk()
    firm_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("firms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)

    instructed_on: Mapped[date | None] = mapped_column(Date)
    due_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")

    # The valuer who will sign. S13 checks their registration covers the asset
    # class before the deliverable can reach `signed`.
    valuer_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    @property
    def requires_registered_valuer(self) -> bool:
        return self.purpose in PURPOSES_REQUIRING_REGISTERED_VALUER
