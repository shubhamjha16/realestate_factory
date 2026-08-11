"""
Redaction utility (S13).

Strips sensitive owner names, survey numbers, and exact GPS coordinates from log strings
and stored audit metadata so no PII reaches log storage.
"""

from __future__ import annotations

import re

# Regex patterns for sensitive PII:
OWNER_RE = re.compile(
    r"\b(owner|proprietor|lessor|lessee|vendor|purchaser|grantor|grantee)\s*:\s*([A-Za-z]+(?:\s+[A-Za-z]+)*?)(?=\s*(?:at|on|in|with|for|dated|survey|,|\.|\n|$))",
    re.IGNORECASE,
)
SURVEY_RE = re.compile(
    r"\b(survey\s+(?:no\.?|number)|gat\s+no\.?|plot\s+no\.?|khasra\s+no\.?)\s*:\s*([A-Za-z0-9/\-\.]+)",
    re.IGNORECASE,
)
COORD_RE = re.compile(
    r"POINT\s*\(\s*[-+]?\d+(?:\.\d+)?\s+[-+]?\d+(?:\.\d+)?\s*\)|[-+]?\d{1,2}\.\d{4,}\s*,\s*[-+]?\d{1,3}\.\d{4,}",
    re.IGNORECASE,
)


def redact_text(text: str) -> str:
    """
    Sanitize text to remove owner names, survey numbers, and GPS coordinates.
    """
    if not text:
        return ""

    out = text
    out = COORD_RE.sub("[REDACTED_COORDINATE]", out)
    out = OWNER_RE.sub(r"\1: [REDACTED_OWNER]", out)
    out = SURVEY_RE.sub(r"\1: [REDACTED_SURVEY]", out)

    return out
