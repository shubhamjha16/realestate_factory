"""
Webhook Engine (S18).

Handles HMAC-SHA256 raw payload signing, signature verification (tamper protection),
and delivery attempt tracking with exponential backoff and dead-letter state.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any


def generate_signature(secret: str, timestamp: int, body: str) -> str:
    """
    Compute HMAC-SHA256 signature over timestamp.body.
    """
    message = f"{timestamp}.{body}".encode()
    key = secret.encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def verify_signature(secret: str, timestamp: int, body: str, signature: str) -> bool:
    """
    Verify HMAC-SHA256 signature against raw body. Rejects any tampered body.
    """
    expected = generate_signature(secret, timestamp, body)
    return hmac.compare_digest(expected, signature)


def deliver_webhook(
    url: str,
    secret: str,
    event_type: str,
    payload: dict[str, Any],
    simulate_failures: int = 0,
    max_retries: int = 3,
) -> dict[str, Any]:
    """
    Deliver webhook callback with HMAC signature and backoff tracking.
    """
    timestamp = int(time.time())
    raw_body = json.dumps(payload, sort_keys=True)
    signature = generate_signature(secret, timestamp, raw_body)

    headers = {
        "Content-Type": "application/json",
        "X-Event-Type": event_type,
        "X-Signature-Timestamp": str(timestamp),
        "X-Signature-256": signature,
    }

    attempts: list[dict[str, Any]] = []
    status = "delivered"

    for attempt_num in range(1, max_retries + 1):
        backoff_seconds = (2 ** (attempt_num - 1)) * 0.5  # 0.5s, 1.0s, 2.0s
        
        if attempt_num <= simulate_failures:
            attempts.append({
                "attempt": attempt_num,
                "status": "failed",
                "http_code": 503,
                "backoff_seconds": backoff_seconds,
                "timestamp": timestamp,
            })
            if attempt_num == max_retries:
                status = "dead_letter"
        else:
            attempts.append({
                "attempt": attempt_num,
                "status": "success",
                "http_code": 200,
                "backoff_seconds": 0.0,
                "timestamp": timestamp,
            })
            status = "delivered"
            break

    return {
        "target_url": url,
        "event_type": event_type,
        "status": status,
        "timestamp": timestamp,
        "signature": signature,
        # The signed headers travel with the delivery record: what a bank
        # verifies is the timestamp and signature it was sent, not one
        # recomputed later from a body that may have been re-serialised.
        "headers": headers,
        "attempts": attempts,
    }
