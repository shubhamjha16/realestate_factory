"""
Server-Sent Events (SSE) router for live job execution progress (S18).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.routers.deps import current_scope
from app.services.access.scope import FirmScope

router = APIRouter(prefix="/api/v1/jobs", tags=["events"])


async def generate_job_events(job_id: str) -> AsyncGenerator[str, None]:
    """
    Simulate live SSE progress narrative stream for a job.
    """
    stages = [
        {"stage": "ingest", "message": "Parsed 34 comparables and title chain documents"},
        {"stage": "adjustments", "message": "Computed 8 location & size adjusted rates"},
        {"stage": "approaches", "message": "Reconciled sales comparison, income, and cost approaches"},
        {"stage": "drafting", "message": "Drafting section 4/9 (Market Analysis)"},
        {"stage": "rendering", "message": "Applying clause registry and generating DOCX cover"},
        {"stage": "completed", "message": "Job completed successfully"},
    ]

    for idx, stg in enumerate(stages):
        event_data = {
            "job_id": job_id,
            "step": idx + 1,
            "total_steps": len(stages),
            "stage": stg["stage"],
            "message": stg["message"],
        }
        yield f"event: progress\ndata: {json.dumps(event_data)}\n\n"
        await asyncio.sleep(0.1)


@router.get("/{job_id}/events", response_model=dict[str, Any])
async def stream_job_events(
    job_id: str,
    scope: FirmScope = Depends(current_scope),
):
    return StreamingResponse(
        generate_job_events(job_id),
        media_type="text/event-stream",
    )
