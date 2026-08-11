"""
Approvals validity and expiry tracking service (S14).

Monitors statutory approvals (Commencement Certificate, Occupation Certificate,
Fire NOC, Environment NOC) and flags items expiring within 90 days.
"""

from __future__ import annotations

from datetime import date
from typing import Any


def check_approvals_expiring_soon(
    approvals: list[dict[str, Any]],
    ref_date: date | None = None,
    within_days: int = 90,
) -> list[dict[str, Any]]:
    """
    Filter approvals and flag items expiring within within_days (default 90 days).
    """
    today = ref_date or date.today()
    flagged: list[dict[str, Any]] = []

    for app in approvals:
        valid_until_raw = app.get("valid_until")
        if not valid_until_raw:
            continue

        if isinstance(valid_until_raw, str):
            try:
                valid_until = date.fromisoformat(valid_until_raw)
            except Exception:
                continue
        elif isinstance(valid_until_raw, date):
            valid_until = valid_until_raw
        else:
            continue

        days_remaining = (valid_until - today).days

        if days_remaining <= within_days:
            flagged.append({
                "kind": app.get("kind", "approval"),
                "issuing_authority": app.get("issuing_authority", "Authority"),
                "valid_until": valid_until.isoformat(),
                "days_remaining": days_remaining,
                "is_expired": days_remaining < 0,
                "is_expiring_soon": 0 <= days_remaining <= within_days,
                "status_warning": "EXPIRED" if days_remaining < 0 else f"EXPIRING IN {days_remaining} DAYS",
            })

    return flagged
