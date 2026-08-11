"""
Quota Enforcement service (S18).

Monitors deliverable and property quotas. Raises HTTP 429 (Too Many Requests) when limits
are exhausted.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

PLAN_QUOTAS: dict[str, int] = {
    "starter": 10,
    "pro": 100,
    "enterprise": 10000,
}


def check_plan_quota(
    plan: str,
    current_usage: int,
    custom_limit: int | None = None,
) -> dict[str, Any]:
    """
    Check if current_usage is within plan limits.
    Raises HTTPException(429) if quota is exhausted.
    """
    limit = custom_limit if custom_limit is not None else PLAN_QUOTAS.get(plan.lower(), 50)

    if current_usage >= limit:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "QuotaExceededError",
                "plan": plan,
                "limit": limit,
                "current_usage": current_usage,
                "message": f"Plan '{plan}' deliverable quota of {limit} exhausted. Upgrade plan to generate more deliverables.",
            },
        )

    return {
        "plan": plan,
        "limit": limit,
        "current_usage": current_usage,
        "remaining": limit - current_usage,
    }
