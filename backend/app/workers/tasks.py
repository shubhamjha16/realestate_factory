"""
Worker tasks.

The web process no longer runs a graph. It writes a job row and enqueues; this
runs. A deploy that restarts the API no longer interrupts a valuation, and a job
that dies mid-graph is retried by arq rather than lost with the process.

Every task is written to be safe to run twice, because at-least-once delivery is
what a queue gives you. `run_generation` refuses a job that is already terminal;
`ocr_document` skips pages it has already written.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.configs.dbConfig import get_sessionmaker
from app.repositories import jobRepository
from app.repositories.jobRepository import TerminalJobError
from app.services import generationService
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def run_generation(
    ctx: dict,
    job_id: str,
    instructions: str,
    property_data: str | None,
    job_type: str | None,
) -> str:
    """
    Run one generation to a terminal state.

    Re-entrant by design: arq retries on failure and redelivers on a lost worker,
    so the first thing this does is claim the job. A job already terminal is left
    exactly as it is — that is the S2 guard doing its work from a second writer,
    which is the case it was built for.
    """
    ident = uuid.UUID(job_id)
    attempt = ctx.get("job_try", 1)

    async with get_sessionmaker()() as db:
        job = await jobRepository.get_unscoped(db, ident)
        if job is None:
            logger.error("job %s was enqueued but does not exist", job_id)
            return "missing"
        if job.terminal_at is not None:
            logger.info("job %s is already terminal (%s); not re-running", job_id, job.status)
            return job.status

        logger.info("job %s starting, attempt %s", job_id, attempt)
        try:
            await generationService.execute(db, ident, instructions, property_data, job_type)
        except TerminalJobError as e:
            # Another worker finished it while this one was running.
            logger.warning("%s", e)

        final = await jobRepository.get_unscoped(db, ident)
        return final.status if final else "unknown"


async def ocr_document(ctx: dict, document_id: str, s3_key: str, page_count: int) -> int:
    """
    OCR a scanned document page by page.

    Title deeds and approvals are scans, often long. Pages are written
    individually and already-written pages are skipped, so a worker killed
    halfway resumes rather than starting again — and never writes a page twice,
    which would duplicate text in the extract the evidence gate (S8) reads.

    The extraction itself lands with the document pipeline in S6; this is the
    resumable shell it runs inside.
    """
    logger.info("ocr %s (%s pages) from %s", document_id, page_count, s3_key)
    raise NotImplementedError(
        "OCR extraction lands in S6 with services/ingest/documents/. "
        "The task and its resume semantics are registered here so S4's queue "
        "topology is complete."
    )


async def sweep_orphans(ctx: dict) -> int:
    """
    Cron. Count jobs left `processing` by a worker that died without arq
    redelivering — a shrinking set as retries land, but not an empty one, and a
    number nobody watches is a number nobody acts on.
    """
    async with get_sessionmaker()() as db:
        stale = await jobRepository.reconcile_orphans(
            db, older_than=datetime.now(UTC) - timedelta(hours=1)
        )
    if stale:
        logger.warning("%s job(s) have been processing for over an hour", stale)
    return stale
