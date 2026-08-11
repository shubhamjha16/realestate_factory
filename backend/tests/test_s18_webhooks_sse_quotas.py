"""
Sprint 18 Integration Surface Tests.

Verifies:
1. Webhook HMAC-SHA256 signature verification & 1-character tamper rejection.
2. 3-attempt backoff & dead-letter state classification.
3. Plan quota rate limiting returning HTTP 429 (Too Many Requests).
4. Server-Sent Events (SSE) progress narrative streaming structure.
"""

from __future__ import annotations

import time

import pytest
from fastapi import HTTPException

from app.routers.events import generate_job_events
from app.services.integration.quotas import check_plan_quota
from app.services.integration.webhookService import (
    deliver_webhook,
    generate_signature,
    verify_signature,
)


def test_webhook_hmac_signature_verification_and_tamper_rejection():
    """Verify HMAC-SHA256 signature succeeds for valid body and rejects tampered body."""
    secret = "whsec_bank_test_key_1234"
    timestamp = int(time.time())
    raw_body = '{"job_id":"job_999","status":"completed","concluded_value":"25000000.00"}'

    # 1. Generate signature
    signature = generate_signature(secret, timestamp, raw_body)

    # 2. Valid body -> signature matches
    assert verify_signature(secret, timestamp, raw_body, signature) is True

    # 3. 1-character tampered body -> signature rejected
    tampered_body = raw_body + " "
    assert verify_signature(secret, timestamp, tampered_body, signature) is False


def test_webhook_backoff_and_dead_letter():
    """Verify 3 failing delivery attempts record exponential backoff and transition to dead-letter state."""
    res = deliver_webhook(
        url="https://bank.sandbox.com/callback",
        secret="whsec_secret",
        event_type="valuation.completed",
        payload={"job_id": "job_101"},
        simulate_failures=3,
        max_retries=3,
    )

    assert res["status"] == "dead_letter"
    assert len(res["attempts"]) == 3
    assert res["attempts"][0]["backoff_seconds"] == 0.5
    assert res["attempts"][1]["backoff_seconds"] == 1.0
    assert res["attempts"][2]["backoff_seconds"] == 2.0


def test_quota_exhaustion_returns_429():
    """Verify plan limit breach raises HTTP 429 (Too Many Requests)."""
    # Starter plan has limit 10
    with pytest.raises(HTTPException) as exc_info:
        check_plan_quota(plan="starter", current_usage=10)

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["error"] == "QuotaExceededError"
    assert exc_info.value.detail["limit"] == 10

    # Within quota -> succeeds cleanly
    ok_res = check_plan_quota(plan="starter", current_usage=5)
    assert ok_res["remaining"] == 5


@pytest.mark.asyncio
async def test_sse_events_stream_structure():
    """Verify SSE streaming progress narrative event formatting."""
    events = []
    async for chunk in generate_job_events("job_test_sse"):
        events.append(chunk)

    assert len(events) == 6
    assert "event: progress" in events[0]
    assert "Parsed 34 comparables" in events[0]
    assert "completed" in events[-1]
