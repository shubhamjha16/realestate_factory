"""
Generation service.

The web process no longer runs a graph. It writes a job row and enqueues; the
arq worker runs it. Two consequences worth stating plainly: a deploy that
restarts the API no longer interrupts a valuation, and a worker that dies
mid-graph gets the job redelivered rather than losing it with the process.

`execute` is the part the worker calls. It is here rather than in
`workers/tasks.py` so that the graph invocation has exactly one definition, and
so a future entry point — a replay tool, a backfill — reuses it instead of
reimplementing the status transitions.
"""

from __future__ import annotations

import asyncio
import uuid

import requests
from arq import create_pool
from sqlalchemy.ext.asyncio import AsyncSession

from app.configs.envConfig import settings
from app.repositories import jobRepository
from app.repositories.jobRepository import TerminalJobError
from app.utils.logger import get_logger
from app.utils.redisClient import redis_settings

logger = get_logger(__name__)


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


def run_graph(job_id: str, instructions: str, property_data: str | None, job_type: str | None) -> dict:
    """Pure invocation, no persistence."""
    from app.services.graph.reGraph import app as graph

    # REState is a TypedDict on a module excluded from mypy; S10 gives the graph
    # a typed builder and this ignore goes away.
    return graph.invoke(  # type: ignore[call-overload]
        initial_state(job_id, instructions, property_data, job_type)
    )


async def enqueue(
    job_id: uuid.UUID, instructions: str, property_data: str | None, job_type: str | None
) -> str | None:
    """
    Hand the job to the queue and return.

    The pool is opened per call rather than held on the app: a long-lived pool
    in the web process is one more thing to drain on shutdown, and enqueueing is
    rare compared with reading. `_job_id` is the job's own id, so arq deduplicates
    a redelivery of the same enqueue rather than starting a second run.
    """
    pool = await create_pool(redis_settings())
    try:
        job = await pool.enqueue_job(
            "run_generation",
            str(job_id),
            instructions,
            property_data,
            job_type,
            _job_id=f"generation:{job_id}",
        )
        return job.job_id if job else None
    finally:
        await pool.close()


async def execute(
    db: AsyncSession,
    job_id: uuid.UUID,
    instructions: str,
    property_data: str | None,
    job_type: str | None,
) -> None:
    """Run one generation to a terminal state. Called by the worker."""
    try:
        await jobRepository.set_status(db, job_id, "processing")
    except TerminalJobError:
        logger.warning("job %s was already terminal; not re-running", job_id)
        return

    try:
        # The graph is synchronous and CPU/IO bound in equal measure; off the
        # loop so one long valuation does not stall the worker's other jobs.
        final = await asyncio.to_thread(
            run_graph, str(job_id), instructions, property_data, job_type
        )
        url = final.get("doc_url") or ""
        if url:
            await jobRepository.set_status(db, job_id, "completed", doc_url=url)
            logger.info("job %s completed: %s", job_id, url)
        else:
            await jobRepository.set_status(
                db, job_id, "failed", error=str(final.get("generation_errors") or "No output")
            )
            logger.warning("job %s produced no document", job_id)
    except TerminalJobError as e:
        logger.warning("%s", e)
    except Exception as e:
        logger.exception("job %s failed: %s", job_id, e)
        try:
            await jobRepository.set_status(db, job_id, "failed", error=str(e))
        except TerminalJobError:
            pass

    await _notify(db, job_id)


async def _notify(db: AsyncSession, job_id: uuid.UUID) -> None:
    """
    Fire-and-forget callback. S18 replaces this with `webhookService.py`: HMAC
    signature over the raw body, backoff, and a `webhook_deliveries` row per
    attempt, which is what a bank's LOS needs before it will trust the call.
    """
    if not settings.WEBHOOK_URL:
        return
    job = await jobRepository.get_unscoped(db, job_id)
    if job is None:
        return
    payload = {
        "job_id": str(job.id),
        "status": job.status,
        "doc_url": job.doc_url,
        "job_type": job.job_type,
        "error": job.error,
    }
    try:
        await asyncio.to_thread(
            lambda: requests.post(settings.WEBHOOK_URL, json=payload, timeout=10)
        )
    except Exception:
        pass
