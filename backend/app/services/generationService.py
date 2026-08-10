"""
Generation service — runs a job through the graph and records its outcome.

Still `threading.Thread`, deliberately: S1 moves code without changing what it
does. S4 replaces `run_in_background` with an arq enqueue, at which point the
web process stops doing work and a restart stops losing jobs.
"""

from __future__ import annotations

import threading
import uuid

import requests

from app.configs.envConfig import settings
from app.repositories import jobRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


def new_job_id() -> str:
    return str(uuid.uuid4())[:12]


def initial_state(job_id: str, instructions: str, property_data: str | None, job_type: str | None) -> dict:
    """The graph's state is a TypedDict with no defaults; every key is seeded here."""
    return {
        "raw_instructions": instructions,
        "raw_property_data": property_data or "",
        "job_type": job_type,
        "_job_id": job_id,
        "doc_type": None, "client_name": None,
        "property_address": None, "property_type": None,
        "purpose": None, "special_notes": None,
        "parsed_data": None, "computed": None,
        "re_research": None, "header_image_path": None,
        "structure_plan": None, "structure_attempt": 0,
        "critic_feedback": None, "_critic_approved": False,
        "section_index": 0, "drafted_sections": None,
        "clause_plan": None,
        "render_attempt": 0, "render_error": None,
        "doc_path": None, "doc_url": None,
        "generation_errors": None,
    }


def run(job_id: str, instructions: str, property_data: str | None, job_type: str | None) -> None:
    jobRepository.update(job_id, status="processing")

    try:
        from app.services.graph.reGraph import app as graph

        # REState is a TypedDict on an excluded module; S10 gives the graph a
        # typed builder and this ignore goes away.
        final = graph.invoke(initial_state(job_id, instructions, property_data, job_type))  # type: ignore[call-overload]

        url = final.get("doc_url") or ""
        if url:
            jobRepository.update(
                job_id,
                status="completed",
                doc_url=url,
                job_type=final.get("doc_type", ""),
            )
            logger.info("job %s completed: %s", job_id, url)
        else:
            jobRepository.update(
                job_id,
                status="failed",
                error=final.get("generation_errors", "No output"),
            )
            logger.warning("job %s produced no document", job_id)

    except Exception as e:
        jobRepository.update(job_id, status="failed", error=str(e))
        logger.exception("job %s failed: %s", job_id, e)

    jobRepository.flush()
    _notify(job_id)


def _notify(job_id: str) -> None:
    """
    Fire-and-forget callback. S18 replaces this with `webhookService.py`: HMAC
    signature, backoff, and a `webhook_deliveries` row per attempt.
    """
    if not settings.WEBHOOK_URL:
        return
    try:
        requests.post(settings.WEBHOOK_URL, json=jobRepository.snapshot(job_id), timeout=10)
    except Exception:
        pass


def run_in_background(job_id: str, instructions: str, property_data: str | None, job_type: str | None) -> None:
    threading.Thread(
        target=run,
        args=(job_id, instructions, property_data, job_type),
        daemon=True,
    ).start()
