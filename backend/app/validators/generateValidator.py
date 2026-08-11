"""
The rules for `POST /generate`.

Kept as plain functions here, and called from `schemas/request/generateRequest.py`
so that FastAPI turns a violation into a 422 naming the field. One definition,
two uses: the schema enforces it on the way in, and S4's worker can re-check a
replayed payload without going through HTTP.
"""

from __future__ import annotations

from app.configs.jobTypes import ALL_JOB_TYPES, ALL_JOB_TYPES_SORTED, VALUATION_TYPES

# A `property_data` payload is a pasted CSV, not an upload. `POST /imports` (S6)
# is the route for anything large; this cap stops a 40 MB string arriving on a
# JSON endpoint and being held in memory for the length of a graph run.
MAX_PROPERTY_DATA_CHARS = 2_000_000
MAX_INSTRUCTIONS_CHARS = 20_000

# Fields a valuation job cannot leave unstated. Market value and liquidation
# value are different figures for the same property; defaulting silently to the
# first is how a report ends up answering a question nobody asked.
REQUIRED_ON_VALUATION = ("basis", "purpose")


def valid_job_types_message() -> str:
    return "valid values: " + ", ".join(ALL_JOB_TYPES_SORTED)


def validate_job_type(job_type: str | None) -> None:
    """`None` is allowed — intake infers it from the instructions, as it always has."""
    if job_type is not None and job_type not in ALL_JOB_TYPES:
        raise ValueError(f"unknown job_type {job_type!r}; {valid_job_types_message()}")


def validate_instructions(instructions: str) -> None:
    if not instructions.strip():
        raise ValueError("instructions required")


def validate_valuation_fields(job_type: str | None, **provided: object) -> None:
    if job_type not in VALUATION_TYPES:
        return
    missing = [name for name in REQUIRED_ON_VALUATION if provided.get(name) is None]
    if missing:
        raise ValueError(
            f"{', '.join(missing)} required for job_type={job_type!r}: a valuation must state "
            f"the basis of value it is reported on and the purpose it is instructed for, and "
            f"neither is safe to default"
        )
