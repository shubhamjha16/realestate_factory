"""
Per-format field definitions — the expected shape, versioned.

A field knows its accepted column spellings, whether it is required, and how to
coerce it. Keeping that in data rather than in each parser's body is what lets
the rejected list say *which field* and *why*, instead of "row 4 failed".
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field as dc_field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.services.valuation.money import MoneyError, to_decimal


class FieldError(ValueError):
    """One field of one row could not be read."""


@dataclass(frozen=True)
class Field:
    name: str
    # Accepted column spellings, in preference order. Matched case-insensitively
    # after whitespace and punctuation are normalised.
    aliases: tuple[str, ...]
    required: bool = False
    coerce: Callable[[Any], Any] | None = None
    default: Any = None
    # A required field can still be legitimately absent — a vacant unit has no
    # tenant and no rent. This says when that is allowed.
    required_unless: tuple[str, ...] = dc_field(default_factory=tuple)


# ── coercions ─────────────────────────────────────────────────────────────────


def as_decimal(value: Any) -> Decimal:
    try:
        return to_decimal(value)
    except MoneyError as e:
        raise FieldError(str(e)) from e


def as_positive_decimal(value: Any) -> Decimal:
    parsed = as_decimal(value)
    if parsed <= 0:
        raise FieldError(f"must be greater than zero, got {parsed}")
    return parsed


def as_non_negative_decimal(value: Any) -> Decimal:
    parsed = as_decimal(value)
    if parsed < 0:
        raise FieldError(f"must not be negative, got {parsed}")
    return parsed


def as_int(value: Any) -> int:
    parsed = as_decimal(value)
    if parsed != parsed.to_integral_value():
        raise FieldError(f"must be a whole number, got {parsed}")
    return int(parsed)


def as_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise FieldError("is empty")
    return text


def as_optional_text(value: Any) -> str:
    return str(value or "").strip()


_DATE_FORMATS = (
    "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d",
    "%d-%b-%Y", "%d %b %Y", "%b %Y", "%d.%m.%Y",
)


def as_date(value: Any) -> date:
    """
    Day-first where ambiguous.

    `03/04/2025` is 3 April in every Indian land record and conveyance, and
    reading it as 3 March would age a comparable by a month — which changes the
    time adjustment applied to it in S7.
    """
    text = str(value or "").strip()
    if not text:
        raise FieldError("is empty")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise FieldError(f"is not a recognisable date: {text!r}")


def as_optional_date(value: Any) -> date | None:
    text = str(value or "").strip()
    return as_date(text) if text else None


def one_of(*allowed: str, default: str | None = None) -> Callable[[Any], str]:
    lowered = {a.lower(): a for a in allowed}

    def _coerce(value: Any) -> str:
        text = str(value or "").strip().lower()
        if not text and default is not None:
            return default
        if text not in lowered:
            raise FieldError(f"must be one of {', '.join(allowed)}, got {text!r}")
        return lowered[text]

    return _coerce
