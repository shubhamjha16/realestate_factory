"""
Job store.

Still the prototype's `jobs.json` under a lock, moved behind a repository
interface so that S2 can replace the implementation with Postgres without any
caller changing. The file store loses jobs on restart and does not survive
concurrent processes — that is the defect S2 exists to close, listed as item 6
in the sprint plan's severity order.
"""

from __future__ import annotations

import json
import os
import threading

JOBS_FILE = os.environ.get("JOBS_FILE", "jobs.json")

_lock = threading.Lock()


def _load() -> dict:
    if os.path.exists(JOBS_FILE):
        try:
            with open(JOBS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


_jobs: dict = _load()


def _flush() -> None:
    with _lock:
        with open(JOBS_FILE, "w") as f:
            json.dump(_jobs, f, indent=2)


def create(job_id: str, job_type: str = "") -> dict:
    with _lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "doc_url": "",
            "job_type": job_type,
            "error": "",
        }
        record = dict(_jobs[job_id])
    _flush()
    return record


def get(job_id: str) -> dict | None:
    return _jobs.get(job_id)


def exists(job_id: str) -> bool:
    return job_id in _jobs


def update(job_id: str, **fields) -> None:
    with _lock:
        if job_id in _jobs:
            _jobs[job_id].update(fields)


def snapshot(job_id: str) -> dict | None:
    with _lock:
        record = _jobs.get(job_id)
        return dict(record) if record else None


def flush() -> None:
    _flush()
