"""
The arq worker.

    arq app.workers.arqApp.WorkerSettings

Deployed as a separate Render service from the same image, so the worker and the
API cannot drift apart in dependencies.
"""

from __future__ import annotations

from arq import cron

from app.utils.logger import get_logger
from app.utils.redisClient import redis_settings
from app.workers.tasks import ocr_document, run_generation, sweep_orphans

logger = get_logger(__name__)


async def startup(ctx: dict) -> None:
    logger.info("worker up")


async def shutdown(ctx: dict) -> None:
    logger.info("worker down")


class WorkerSettings:
    functions = [run_generation, ocr_document]
    cron_jobs = [cron(sweep_orphans, minute={0, 30}, run_at_startup=False)]

    redis_settings = redis_settings()
    on_startup = startup
    on_shutdown = shutdown

    # A valuation with a long section loop is minutes, not seconds. The default
    # 300s would kill a legitimate job and then retry it, which is worse than
    # slow.
    job_timeout = 1800

    # Retries are for a crashed worker or a provider blip. Three is enough to
    # ride out both; beyond that the job is failing for a reason retrying will
    # not fix, and it should surface rather than churn through the ledger.
    max_tries = 3
    retry_jobs = True

    max_jobs = 10
    keep_result = 3600
