"""
Jobs.

Replaces `jobs.json`. A restart used to lose every in-flight job; now a job that
was mid-graph when the process died is still there, in `processing`, and
reconcilable — the sweep that terminates it belongs to S4, but the record exists
to be swept.

`terminal_at` is the finality marker. Once it is set the row's status is frozen,
enforced in `jobRepository`, because a completed deliverable that later flips to
`failed` (or the reverse) is a record a bank cannot rely on.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk

JOB_STATUSES = ("queued", "processing", "completed", "failed", "blocked_evidence")
TERMINAL_STATUSES = frozenset({"completed", "failed", "blocked_evidence"})


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        # The idempotency key (S4) is SHA-256 of normalised instructions + job_type
        # + import checksums + firm_id. Unique so a double submit is one execution.
        Index("uq_jobs_idempotency_key", "idempotency_key", unique=True,
              postgresql_where=text("idempotency_key IS NOT NULL")),
        Index("ix_jobs_firm_created", "firm_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()

    # Nullable until S5 lands auth: today there is no firm to attribute a job to,
    # and a NOT NULL column with a fabricated default would be a lie in the data.
    firm_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("firms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    mandate_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("mandates.id", ondelete="SET NULL"), index=True
    )

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="queued", index=True)
    job_type: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    instructions: Mapped[str] = mapped_column(Text, nullable=False, default="")
    import_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(PGUUID(as_uuid=True)))
    idempotency_key: Mapped[str | None] = mapped_column(String(64))

    doc_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")

    terminal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def is_terminal(self) -> bool:
        return self.terminal_at is not None
