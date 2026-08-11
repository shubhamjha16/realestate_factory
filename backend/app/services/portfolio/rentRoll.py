"""
Rent Roll & WAULT calculation service (S16).

Computes exact rupee rent roll aggregation, Weighted Average Unexpired Lease Term (WAULT)
in years, and lease expiry profiles.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any


def compute_rent_roll_and_wault(
    leases: Sequence[dict[str, Any]],
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """
    Compute portfolio rent roll metrics, exact rupee total, WAULT (years), and expiry profile.
    """
    ref_date = as_of_date or date.today()

    total_monthly_rent = Decimal("0.00")
    total_leased_area = Decimal("0.00")
    weighted_unexpired_term_sum = Decimal("0.00")
    total_annual_rent = Decimal("0.00")

    expiry_profile: dict[str, dict[str, Any]] = {
        "less_than_1_yr": {"count": 0, "annual_rent": Decimal("0.00")},
        "1_to_3_yrs": {"count": 0, "annual_rent": Decimal("0.00")},
        "3_to_5_yrs": {"count": 0, "annual_rent": Decimal("0.00")},
        "more_than_5_yrs": {"count": 0, "annual_rent": Decimal("0.00")},
    }

    processed_leases = []

    for lease in leases:
        tenant = lease.get("tenant_name", "Tenant")
        area = Decimal(str(lease.get("area", 0))).quantize(Decimal("0.01"))
        m_rent = Decimal(str(lease.get("monthly_rent", 0))).quantize(Decimal("0.01"))
        a_rent = (m_rent * Decimal("12")).quantize(Decimal("0.01"))

        expiry_raw = lease.get("lease_expiry")
        if isinstance(expiry_raw, str):
            expiry_dt = date.fromisoformat(expiry_raw)
        elif isinstance(expiry_raw, date):
            expiry_dt = expiry_raw
        else:
            expiry_dt = ref_date

        days_remaining = max(0, (expiry_dt - ref_date).days)
        unexpired_years = Decimal(str(days_remaining / 365.25)).quantize(Decimal("0.0001"))

        total_monthly_rent += m_rent
        total_annual_rent += a_rent
        total_leased_area += area
        weighted_unexpired_term_sum += (unexpired_years * a_rent)

        # Categorize expiry profile
        if unexpired_years < Decimal("1.0"):
            expiry_profile["less_than_1_yr"]["count"] += 1
            expiry_profile["less_than_1_yr"]["annual_rent"] += a_rent
        elif Decimal("1.0") <= unexpired_years < Decimal("3.0"):
            expiry_profile["1_to_3_yrs"]["count"] += 1
            expiry_profile["1_to_3_yrs"]["annual_rent"] += a_rent
        elif Decimal("3.0") <= unexpired_years < Decimal("5.0"):
            expiry_profile["3_to_5_yrs"]["count"] += 1
            expiry_profile["3_to_5_yrs"]["annual_rent"] += a_rent
        else:
            expiry_profile["more_than_5_yrs"]["count"] += 1
            expiry_profile["more_than_5_yrs"]["annual_rent"] += a_rent

        processed_leases.append({
            "tenant_name": tenant,
            "area_sqft": str(area),
            "monthly_rent": str(m_rent),
            "annual_rent": str(a_rent),
            "lease_expiry": expiry_dt.isoformat(),
            "unexpired_years": str(unexpired_years.quantize(Decimal("0.01"))),
        })

    if total_annual_rent > Decimal("0.00"):
        wault_years = (weighted_unexpired_term_sum / total_annual_rent).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        wault_years = Decimal("0.00")

    return {
        "as_of_date": ref_date.isoformat(),
        "total_active_leases": len(leases),
        "total_leased_area_sqft": str(total_leased_area),
        "total_monthly_rent": str(total_monthly_rent),
        "total_annual_rent": str(total_annual_rent),
        "wault_years": str(wault_years),
        "expiry_profile": {
            k: {"count": v["count"], "annual_rent": str(v["annual_rent"])}
            for k, v in expiry_profile.items()
        },
        "leases": processed_leases,
    }
