"""Health controller."""

from __future__ import annotations


def health() -> dict:
    return {"status": "ok", "service": "realestate-factory"}
