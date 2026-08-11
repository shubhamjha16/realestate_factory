"""
Figure provenance validator — Real Estate Factory.

Enforces the core product separation: no number (monetary figure or valuation conclusion)
may appear in rendered section prose unless it came from a `valuation_line`, computed
metrics, or input parameters.

A figure invented in prose by an LLM raises `UnprovenancedFigureError` and blocks render.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

# Regex to catch Indian currency / monetary expressions with optional commas and denomination:
# e.g., ₹4.2 crore, ₹ 4.2 crore, ₹ 1,50,00,000, Rs 4.2 crore, 4.2 crore rupees, ₹4.2Cr
MONEY_PROSE_RE = re.compile(
    r"(?:₹|Rs\.?|INR)\s*([0-9,]+(?:\.[0-9]+)?)\s*(crore|lakh|cr|lakhs)?|"
    r"([0-9,]+(?:\.[0-9]+)?)\s*(crore|lakh|cr|lakhs)\s*(?:rupees|inr|₹)?",
    re.IGNORECASE,
)


class UnprovenancedFigureError(ValueError):
    """Raised when rendered prose contains a numerical monetary figure not backed by valuation lines or computed metrics."""

    def __init__(self, unprovenanced_text: str, figure_val: Decimal, section_heading: str):
        self.unprovenanced_text = unprovenanced_text
        self.figure_val = figure_val
        self.section_heading = section_heading
        super().__init__(
            f"Unprovenanced figure in section {section_heading!r}: "
            f"prose contains {unprovenanced_text!r} ({figure_val}), but no valuation line or computed record holds this amount."
        )


def _parse_indian_denominated_value(num_str: str, denom: str) -> Decimal:
    """Convert number string and denomination (crore/lakh) to absolute Decimal value."""
    base = Decimal(num_str.replace(",", ""))
    denom_clean = (denom or "").lower().strip()
    if denom_clean in ("crore", "lakh", "cr", "lakhs"):
        if denom_clean in ("crore", "cr"):
            return base * Decimal("10000000")  # 1 Crore = 10,000,000
        if denom_clean in ("lakh", "lakhs"):
            return base * Decimal("100000")    # 1 Lakh = 100,000
    return base


def _extract_all_numbers(obj: Any, out_set: set[Decimal]) -> None:
    """Recursively harvest all valid numbers from valuation_lines, computed dict, etc."""
    if isinstance(obj, (int, float)):
        try:
            d = Decimal(str(obj))
            if not d.is_nan() and not d.is_infinite():
                out_set.add(d)
        except Exception:
            pass
    elif isinstance(obj, Decimal):
        if not obj.is_nan() and not obj.is_infinite():
            out_set.add(obj)
    elif isinstance(obj, str):
        for match in re.findall(r"\d+(?:\.\d+)?", obj.replace(",", "")):
            try:
                d = Decimal(match)
                if not d.is_nan() and not d.is_infinite():
                    out_set.add(d)
            except Exception:
                pass
    elif isinstance(obj, dict):
        for v in obj.values():
            _extract_all_numbers(v, out_set)
    elif isinstance(obj, (list, tuple, set)):
        for item in obj:
            _extract_all_numbers(item, out_set)


def validate_figure_provenance(
    clause_plan: Sequence[dict],
    valuation_lines: Sequence[dict] | None = None,
    computed: dict | None = None,
    raw_instructions: str = "",
) -> None:
    """
    Scan clause plan prose content for monetary figures and verify their provenance.
    
    Raises UnprovenancedFigureError if prose contains an invented money figure.
    """
    allowed_numbers: set[Decimal] = set()

    # Populate allowed pool from valuation_lines, computed, and raw instructions
    if valuation_lines:
        _extract_all_numbers(valuation_lines, allowed_numbers)
    if computed:
        _extract_all_numbers(computed, allowed_numbers)
    if raw_instructions:
        _extract_all_numbers(raw_instructions, allowed_numbers)

    for clause in clause_plan:
        heading = clause.get("heading", "Section")
        content = clause.get("content", "")
        if not content:
            continue

        for match in MONEY_PROSE_RE.finditer(content):
            full_match_text = match.group(0)
            num_part = match.group(1) or match.group(3)
            denom_part = match.group(2) or match.group(4)

            if not num_part:
                continue

            try:
                figure_val = _parse_indian_denominated_value(num_part, denom_part)
            except Exception:
                continue

            # Check if this figure value (or exact number) exists in allowed pool
            found = False
            if figure_val in allowed_numbers:
                found = True
            else:
                for allowed in allowed_numbers:
                    if abs(allowed - figure_val) < Decimal("0.01"):
                        found = True
                        break

            if not found:
                raise UnprovenancedFigureError(full_match_text, figure_val, heading)
