"""Response schemas for the generation and job surfaces."""

from __future__ import annotations

from pydantic import BaseModel


class JobStatus(BaseModel):
    job_id: str
    status: str
    doc_url: str = ""
    job_type: str = ""
    error: str = ""
