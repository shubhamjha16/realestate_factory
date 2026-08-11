"""
Request schemas for the generation surface.

Constraints are declared on the fields so FastAPI answers with a 422 that names
the offending field and lists what was acceptable, rather than a 400 carrying a
sentence the client has to parse. The rules that need more than one field are in
`validators/generateValidator.py` and called from here.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from app.configs.jobTypes import ALL_JOB_TYPES_SORTED
from app.validators.generateValidator import (
    MAX_INSTRUCTIONS_CHARS,
    MAX_PROPERTY_DATA_CHARS,
    validate_instructions,
    validate_valuation_fields,
)

# A Literal over the registry, so the 422 lists every acceptable value and the
# generated TypeScript is a union rather than `string`.
JobTypeLiteral = Literal[ALL_JOB_TYPES_SORTED]  # type: ignore[valid-type]

ValuationBasis = Literal["market", "fair", "liquidation", "distress", "insurable"]
ValuationPremise = Literal["existing_use", "highest_best_use"]
MandatePurpose = Literal["loan", "ibc", "dispute", "financial_reporting", "internal"]


class GenerateRequest(BaseModel):
    instructions: Annotated[str, Field(min_length=1, max_length=MAX_INSTRUCTIONS_CHARS)]

    property_data: Annotated[str, Field(max_length=MAX_PROPERTY_DATA_CHARS)] = ""

    # Optional: intake still infers it from the instructions when it is absent.
    # Given, it must be a type this engine actually serves.
    job_type: JobTypeLiteral | None = None

    basis: ValuationBasis | None = None
    premise: ValuationPremise | None = None
    purpose: MandatePurpose | None = None

    @model_validator(mode="after")
    def _check(self) -> GenerateRequest:
        validate_instructions(self.instructions)
        validate_valuation_fields(
            self.job_type, basis=self.basis, purpose=self.purpose, premise=self.premise
        )
        return self
