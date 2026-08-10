"""Request schemas for the generation surface."""

from __future__ import annotations

from pydantic import BaseModel


class GenerateRequest(BaseModel):
    instructions: str
    property_data: str | None = ""   # CSV of comparables / lease schedule / etc.
    job_type: str | None = None
