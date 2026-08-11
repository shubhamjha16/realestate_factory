"""
Construction Disbursement Verification service (S16).

Validates tranche disbursement requests against certified physical completion stage percentage.
A request exceeding the certified stage percentage is flagged and blocked.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def verify_disbursement_request(
    certified_stage_pct: Decimal,
    requested_tranche_pct: Decimal,
    prior_disbursed_pct: Decimal = Decimal("0.00"),
) -> dict[str, Any]:
    """
    Validate disbursement request against certified physical progress percentage.
    """
    certified_q = Decimal(str(certified_stage_pct)).quantize(Decimal("0.01"))
    tranche_q = Decimal(str(requested_tranche_pct)).quantize(Decimal("0.01"))
    prior_q = Decimal(str(prior_disbursed_pct)).quantize(Decimal("0.01"))

    cumulative_requested = prior_q + tranche_q

    if cumulative_requested > certified_q:
        approved = False
        status_code = "FLAGGED_EXCEEDS_CERTIFIED_STAGE"
        message = (
            f"Disbursement request ({cumulative_requested}%) exceeds certified physical "
            f"completion stage ({certified_q}%). Payment authorization blocked."
        )
    else:
        approved = True
        status_code = "ELIGIBLE_FOR_DISBURSEMENT"
        message = (
            f"Disbursement request ({cumulative_requested}%) is within certified physical "
            f"completion stage ({certified_q}%)."
        )

    return {
        "approved": approved,
        "status_code": status_code,
        "certified_stage_pct": str(certified_q),
        "prior_disbursed_pct": str(prior_q),
        "requested_tranche_pct": str(tranche_q),
        "cumulative_requested_pct": str(cumulative_requested),
        "message": message,
    }
