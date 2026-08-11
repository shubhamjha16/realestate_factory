"""
Generation service.

Still `threading.Thread`, deliberately: S4 replaces it with an arq enqueue. What
changed in S2 is where the job *lives* — Postgres, not a rewritten JSON file —
so killing this process no longer erases the record of what was running.

The worker thread opens its own session. A session is not thread-safe and the
request's session is closed the moment the response is returned, so sharing one
would be a use-after-free with extra steps.
"""

from __future__ import annotations

import asyncio
import threading
import uuid

import requests
from sqlalchemy.ext.asyncio import AsyncSession

from app.configs.dbConfig import get_sessionmaker
from app.configs.envConfig import settings
from app.repositories import jobRepository
from app.repositories.jobRepository import TerminalJobError
from app.utils.logger import get_logger

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
    """Pure invocation, no persistence. Separate so S4's arq task can reuse it."""
    from app.services.graph.reGraph import app as graph

    # REState is a TypedDict on a module excluded from mypy; S10 gives the graph
    # a typed builder and this ignore goes away.
    return graph.invoke(  # type: ignore[call-overload]
        initial_state(job_id, instructions, property_data, job_type)
    )


async def execute(
    db: AsyncSession,
    job_id: uuid.UUID,
    instructions: str,
    property_data: str | None,
    job_type: str | None,
) -> None:
    try:
        await jobRepository.set_status(db, job_id, "processing")
    except TerminalJobError:
        logger.warning("job %s was already terminal; not re-running", job_id)
        return

    try:
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
    job = await jobRepository.get(db, job_id)
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


def run_in_background(
    job_id: uuid.UUID, instructions: str, property_data: str | None, job_type: str | None
) -> None:
    """
    Hand the job to a thread with its own event loop and its own session.

    This is the line S4 deletes, replacing it with `arq.enqueue_job`. Until then
    the web process still does the work, and a deploy still interrupts whatever
    is in flight — the difference is that the interrupted job is now a row
    someone can find.
    """

    def _worker() -> None:
        async def _main() -> None:
            async with get_sessionmaker()() as db:
                await execute(db, job_id, instructions, property_data, job_type)

        asyncio.run(_main())

    threading.Thread(target=_worker, daemon=True).start()
