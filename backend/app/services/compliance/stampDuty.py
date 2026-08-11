"""
Stamp Duty & Registration Fee service (S14).

Computes stamp duty applying state rate tables and enforcing the **circle-rate floor rule**:
taxable consideration is `max(agreed_consideration, circle_rate * area)`.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

STATE_STAMP_RATES: dict[str, dict[str, Decimal]] = {
    "maharashtra": {"default": Decimal("0.05"), "male": Decimal("0.05"), "female": Decimal("0.04")},
    "delhi": {"default": Decimal("0.06"), "male": Decimal("0.06"), "female": Decimal("0.04")},
    "karnataka": {"default": Decimal("0.05"), "male": Decimal("0.05"), "female": Decimal("0.05")},
    "uttar_pradesh": {"default": Decimal("0.07"), "male": Decimal("0.07"), "female": Decimal("0.06")},
}

REGISTRATION_FEE_RATE = Decimal("0.01")  # 1% standard registration fee


def compute_stamp_duty(
    state: str,
    document_type: str,
    consideration: Decimal,
    circle_rate: Decimal,
    area: Decimal,
    gender: str = "male",
) -> dict[str, Any]:
    """
    Compute stamp duty and registration fee for conveyance / transaction documents.
    Enforces the circle-rate floor rule: taxable_value = max(consideration, circle_rate * area).
    """
    state_clean = (state or "").lower().strip().replace(" ", "_")
    rates = STATE_STAMP_RATES.get(state_clean, STATE_STAMP_RATES["maharashtra"])

    gender_clean = (gender or "male").lower().strip()
    stamp_rate = rates.get(gender_clean, rates["default"])

    consideration_q = Decimal(str(consideration)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    circle_rate_q = Decimal(str(circle_rate)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    area_q = Decimal(str(area)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    circle_valuation = (circle_rate_q * area_q).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    if consideration_q >= circle_valuation:
        taxable_value = consideration_q
        applied_basis = "agreed_consideration"
    else:
        taxable_value = circle_valuation
        applied_basis = "circle_rate_floor"

    stamp_duty_amount = (taxable_value * stamp_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    registration_fee = (taxable_value * REGISTRATION_FEE_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    total_statutory_dues = stamp_duty_amount + registration_fee

    return {
        "state": state.title(),
        "document_type": document_type,
        "agreed_consideration": str(consideration_q),
        "circle_rate_per_unit": str(circle_rate_q),
        "area": str(area_q),
        "circle_valuation": str(circle_valuation),
        "taxable_value": str(taxable_value),
        "applied_basis": applied_basis,
        "stamp_duty_rate": str(stamp_rate),
        "stamp_duty_amount": str(stamp_duty_amount),
        "registration_fee_amount": str(registration_fee),
        "total_statutory_dues": str(total_statutory_dues),
    }
