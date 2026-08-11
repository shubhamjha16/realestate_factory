"""Response schemas for the generation and job surfaces."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.job import Job


class JobStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    status: str
    doc_url: str = ""
    job_type: str = ""
    error: str = ""
    # Absent until the job finishes. Present means the record is frozen — the
    # repository refuses further status writes (S2).
    terminal_at: datetime | None = None

    @classmethod
    def of(cls, job: Job) -> JobStatus:
        return cls(
            job_id=str(job.id),
            status=job.status,
            doc_url=job.doc_url,
            job_type=job.job_type,
            error=job.error,
            terminal_at=job.terminal_at,
        )


class JobListResponse(BaseModel):
    jobs: list[JobStatus] = Field(default_factory=list)


__all__ = ["JobStatus", "JobListResponse", "uuid"]
