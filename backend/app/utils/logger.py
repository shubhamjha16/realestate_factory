"""
Logging.

Plain stdlib logging for S1. S19 replaces this with structlog carrying
`job_id`/`mandate_id` correlation through `redaction.py`, so that a job id alone
reconstructs a lifecycle and no owner name or survey number reaches log storage.
"""

from __future__ import annotations

import logging
import sys

from app.configs.envConfig import settings

_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s | %(message)s"))
    root = logging.getLogger("app")
    root.setLevel(settings.LOG_LEVEL.upper())
    root.addHandler(handler)
    root.propagate = False
    _configured = True


def get_logger(name: str) -> logging.Logger:
    _configure()
    return logging.getLogger(name if name.startswith("app") else f"app.{name}")
