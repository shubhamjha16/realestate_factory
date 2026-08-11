"""
Firm-Scoped Reporting Corpus Retrieval service (S17).

Enforces strict multi-tenancy: retrieval is scoped per firm (`scope.firm_id`) and **never across clients**.
Attempting cross-firm retrieval returns empty results and logs an `AuditEvent` with `action="retrieval_cross_firm_attempt"`.
Retrieval feeds commentary only — **never figures or factual assertions**.
"""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from app.repositories import auditRepository
from app.services.access.scope import FirmScope

# In-memory sample corpus for firm house wording lookup
SAMPLE_CORPUS: list[dict[str, Any]] = [
    {
        "id": "c1",
        "firm_id": "11111111-1111-1111-1111-111111111111",
        "locality": "BKC",
        "city": "Mumbai",
        "topic": "market_analysis",
        "content": (
            "Bandra-Kurla Complex (BKC) remains Mumbai's premier Grade-A commercial hub, "
            "benefiting from superior infrastructure, high institutional tenant retention, "
            "and strong capital appreciation trends."
        ),
    },
    {
        "id": "c2",
        "firm_id": "11111111-1111-1111-1111-111111111111",
        "locality": "Sector 62",
        "city": "Noida",
        "topic": "market_analysis",
        "content": (
            "Sector 62, Noida is an established IT/ITeS micro-market with direct Metro connectivity "
            "and steady absorption driven by technology occupiers."
        ),
    },
    {
        "id": "c3",
        "firm_id": "99999999-9999-9999-9999-999999999999",  # Firm B corpus item
        "locality": "Whitefield",
        "city": "Bengaluru",
        "topic": "market_analysis",
        "content": "Whitefield commercial corridor exhibits robust tech park occupancy.",
    },
]


def filter_commentary_only(text: str) -> str:
    """
    Ensure retrieved text contains commentary/qualitative wording only.
    Strips unprovenanced specific monetary amounts (e.g. ₹ 50,000 / sqft)
    so figures must come from valuation_lines.
    """
    # Replace standalone currency figures with generic text if any exist
    clean = re.sub(r"₹\s*[\d,]+(?:\.\d+)?", "[VALUATION_LINE_FIGURE]", text)
    return clean


async def search_firm_corpus(
    db: Any,
    scope: FirmScope,
    target_firm_id: UUID | str,
    locality: str = "",
    topic: str = "",
) -> dict[str, Any]:
    """
    Search firm's past valuation corpus.
    If target_firm_id != scope.firm_id, log cross-firm audit event and return empty.
    """
    target_firm_str = str(target_firm_id).lower()
    scope_firm_str = str(scope.firm_id).lower()

    if target_firm_str != scope_firm_str:
        # A cross-firm attempt is refused whether or not the event can be
        # written. `audit_logged` reports what actually happened rather than
        # what was intended — a caller told an event was recorded when none was
        # has no way to discover the difference.
        audit_logged = False
        if db is not None:
            await auditRepository.record_audit_event(
                db=db,
                scope=scope,
                action="retrieval_cross_firm_attempt",
                resource="corpus",
                meta={
                    "target_firm_id": target_firm_str,
                    "scope_firm_id": scope_firm_str,
                    "locality": locality,
                },
            )
            audit_logged = True

        return {
            "results": [],
            "audit_logged": audit_logged,
            "error": "Cross-firm retrieval attempt blocked and logged.",
        }

    # Same firm -> filter corpus by scope.firm_id
    matches = []
    locality_clean = locality.lower().strip()

    for item in SAMPLE_CORPUS:
        if item["firm_id"].lower() == scope_firm_str:
            if not locality_clean or locality_clean in item["locality"].lower() or locality_clean in item["content"].lower():
                matches.append({
                    "id": item["id"],
                    "locality": item["locality"],
                    "city": item["city"],
                    "topic": item["topic"],
                    "content": filter_commentary_only(item["content"]),
                })

    return {
        "results": matches,
        "audit_logged": False,
        "error": None,
    }
