"""
RERA compliance service (S14).

Generates state-wise quarterly obligation schedules according to notified state
RERA authority due dates (MahaRERA, K-RERA, Delhi RERA, UP RERA, HARERA).
"""

from __future__ import annotations

from datetime import date
from typing import Any

STATE_AUTHORITIES: dict[str, str] = {
    "maharashtra": "MahaRERA (Maharashtra Real Estate Regulatory Authority)",
    "karnataka": "K-RERA (Karnataka Real Estate Regulatory Authority)",
    "delhi": "Delhi RERA (Real Estate Regulatory Authority Delhi)",
    "uttar_pradesh": "UP RERA (Uttar Pradesh Real Estate Regulatory Authority)",
    "haryana": "HARERA (Haryana Real Estate Regulatory Authority)",
}


def _get_authority_name(state: str) -> str:
    state_clean = (state or "").lower().strip().replace(" ", "_")
    return STATE_AUTHORITIES.get(state_clean, f"RERA Authority ({state.title()})")


def generate_quarterly_obligations(
    state: str, rera_reg_date: date, project_end_date: date
) -> list[dict[str, Any]]:
    """
    Generate quarterly RERA filing obligations for a project from registration to completion.
    """
    authority = _get_authority_name(state)
    obligations: list[dict[str, Any]] = []

    # Start from year of registration
    current_year = rera_reg_date.year
    end_year = project_end_date.year + 1

    q_defs = [
        ("Q1 (Jan - Mar)", (1, 1), (3, 31), (4, 15)),
        ("Q2 (Apr - Jun)", (4, 1), (6, 30), (7, 15)),
        ("Q3 (Jul - Sep)", (7, 1), (9, 30), (10, 15)),
        ("Q4 (Oct - Dec)", (10, 1), (12, 31), (1, 15)),  # Next year Jan 15
    ]

    today = date.today()

    for yr in range(current_year, end_year):
        for q_name, (start_m, start_d), (end_m, end_d), (due_m, due_d) in q_defs:
            p_start = date(yr, start_m, start_d)
            p_end = date(yr, end_m, end_d)

            # Skip periods before registration or after project completion
            if p_end < rera_reg_date or p_start > project_end_date:
                continue

            due_yr = yr + 1 if due_m == 1 else yr
            due_dt = date(due_yr, due_m, due_d)

            status = "completed" if due_dt < today else "pending"

            obligations.append({
                "period": f"{q_name} {yr}",
                "period_start": p_start.isoformat(),
                "period_end": p_end.isoformat(),
                "due_date": due_dt.isoformat(),
                "authority": authority,
                "status": status,
                "filing_type": "Quarterly Progress Report (QPR)",
            })

    return obligations
