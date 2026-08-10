"""
Validation for `POST /generate`.

S1 carries forward exactly the one rule the prototype enforced, so that the
restructuring changes no response. S3 adds the rest: `job_type` must be in
`ALL_JOB_TYPES` with the valid values listed in the 422, a payload cap, and
`basis` and `purpose` required on valuation jobs rather than defaulted.
"""

from __future__ import annotations

from fastapi import HTTPException

from app.schemas.request.generateRequest import GenerateRequest


def validate_generate(req: GenerateRequest) -> None:
    if not req.instructions.strip():
        raise HTTPException(400, "instructions required")
