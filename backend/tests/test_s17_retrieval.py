"""
Sprint 17 Reporting Corpus Retrieval Tests.

Verifies:
1. Firm-scoped house wording commentary retrieval.
2. Cross-firm retrieval attempts return [] and trigger audit logging.
3. Commentary-only filter strips unprovenanced financial numbers.
"""

from __future__ import annotations

import uuid

import pytest

from app.services.access.scope import FirmScope
from app.services.retrieval.corpus import filter_commentary_only, search_firm_corpus

FIRM_A_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
FIRM_B_ID = uuid.UUID("99999999-9999-9999-9999-999999999999")
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")

SCOPE_A = FirmScope(firm_id=FIRM_A_ID, user_id=USER_ID, role="analyst")


class RecordingSession:
    """
    The narrowest thing `record_audit_event` needs. The cross-firm assertion is
    worthless against `db=None` — nothing can be written, so `audit_logged`
    would only be echoing a literal. This captures the row instead.
    """

    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None


@pytest.mark.asyncio
async def test_same_firm_commentary_retrieval():
    """Verify searching own firm corpus returns matching house wording snippets."""
    res = await search_firm_corpus(
        db=None,
        scope=SCOPE_A,
        target_firm_id=FIRM_A_ID,
        locality="BKC",
    )

    assert res["audit_logged"] is False
    assert len(res["results"]) >= 1
    assert "Bandra-Kurla Complex" in res["results"][0]["content"]


@pytest.mark.asyncio
async def test_cross_firm_retrieval_attempt_returns_empty_and_logs_audit_event():
    """
    Verify attempting to retrieve across a firm boundary (Firm A searching Firm B)
    returns empty results and logs an audit event.
    """
    db = RecordingSession()
    res = await search_firm_corpus(
        db=db,
        scope=SCOPE_A,
        target_firm_id=FIRM_B_ID,
        locality="Whitefield",
    )

    assert res["results"] == []
    assert res["audit_logged"] is True
    assert "Cross-firm" in res["error"]

    # The event is a real row, not a flag in the response.
    assert len(db.added) == 1
    event = db.added[0]
    assert event.action == "retrieval_cross_firm_attempt"
    assert event.firm_id == FIRM_A_ID
    assert event.meta["target_firm_id"] == str(FIRM_B_ID)


def test_commentary_only_filter_strips_unprovenanced_figures():
    """Verify commentary-only filter replaces specific financial figures."""
    raw_text = "The prevailing market rate in BKC is ₹ 55,000 / sqft, reflecting 12% annual growth."
    filtered = filter_commentary_only(raw_text)

    assert "₹ 55,000" not in filtered
    assert "[VALUATION_LINE_FIGURE]" in filtered
