"""
Money.

Every figure in this system is a `Decimal`. Property values run to crores, and
`round(area * rate, 2)` on binary floats produces figures that will not reconcile
across a portfolio — a total summed per property and summed in aggregate disagree
by paise, then by rupees, and by the time anyone notices it is in a signed report.

Two rules, and the second is the one people get wrong:

  1. **Parse from strings, never from floats.** `Decimal(0.1)` is
     `0.1000000000000000055511151231257827021181583404541015625`. `Decimal("0.1")`
     is a tenth.
  2. **Round once, at the end, and only for presentation.** Intermediate
     rounding is how a rent roll stops tying to its lines. `quantize` exists here
     for the boundary — writing to a `NUMERIC(18,2)` column, or rendering — and
     is not to be sprinkled through a calculation.

The policy is half-up, matching `ROUNDING_POLICY` in the environment and Indian
commercial convention: 0.5 rounds away from zero, not to even.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, InvalidOperation, localcontext

from app.configs.envConfig import settings

# NUMERIC(18,2). Every monetary column in the schema.
MONEY_EXPONENT = Decimal("0.01")
# Rates, areas and percentages carry more places, because they are multiplied
# before they are rounded.
RATE_EXPONENT = Decimal("0.0001")
PERCENT_EXPONENT = Decimal("0.0001")

ZERO = Decimal("0")

_ROUNDING = {"half_up": ROUND_HALF_UP, "half_even": ROUND_HALF_EVEN}


def rounding_mode() -> str:
    return _ROUNDING[settings.ROUNDING_POLICY]


class MoneyError(ValueError):
    """A value that cannot be money. Raised rather than coerced to zero."""


def to_decimal(value: object, *, field: str = "value") -> Decimal:
    """
    Parse anything a spreadsheet might hold into an exact Decimal.

    Handles `₹`, `Rs`, `Rs.`, thousands separators in both Western and Indian
    grouping, a trailing `/-`, and parenthesised negatives. Refuses everything
    else — a figure this cannot read is a figure a human must look at, not a
    silent zero that flows into a total.
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        # Deliberate: accepting a float here would launder the very imprecision
        # this module exists to keep out.
        raise MoneyError(
            f"{field} was passed a float ({value!r}). Money is parsed from strings; "
            f"a float has already lost the exact value."
        )

    text = str(value).strip()
    if not text:
        raise MoneyError(f"{field} is empty")

    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]

    for token in ("₹", "rs.", "rs", "inr", ",", " ", "/-", "_"):
        text = text.lower().replace(token, "")

    if not text or text in {"-", "."}:
        raise MoneyError(f"{field} is not a number: {value!r}")

    try:
        parsed = Decimal(text)
    except InvalidOperation as e:
        raise MoneyError(f"{field} is not a number: {value!r}") from e

    if not parsed.is_finite():
        raise MoneyError(f"{field} is not finite: {value!r}")
    return -parsed if negative else parsed


def try_decimal(value: object, default: Decimal | None = None) -> Decimal | None:
    """For fields that are genuinely optional. Never used for a figure that must exist."""
    try:
        return to_decimal(value)
    except MoneyError:
        return default


def quantize_money(value: Decimal) -> Decimal:
    """
    To the paisa, for a boundary — a NUMERIC(18,2) column, or rendered output.
    Not for intermediate steps.
    """
    with localcontext() as ctx:
        ctx.rounding = rounding_mode()
        return value.quantize(MONEY_EXPONENT)


def quantize_rate(value: Decimal) -> Decimal:
    with localcontext() as ctx:
        ctx.rounding = rounding_mode()
        return value.quantize(RATE_EXPONENT)


def quantize_percent(value: Decimal) -> Decimal:
    with localcontext() as ctx:
        ctx.rounding = rounding_mode()
        return value.quantize(PERCENT_EXPONENT)


def total(values: Iterable[Decimal]) -> Decimal:
    """
    Sum exactly, then round once.

    This is what makes a 200-property portfolio total identically whether it is
    summed per property or in aggregate. Rounding each addend first does not.
    """
    return quantize_money(sum(values, ZERO))


def safe_divide(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    """
    `None` on a zero denominator, not zero.

    A yield of 0% and a yield that could not be computed are different facts, and
    a report should say which one it means.
    """
    if denominator == 0:
        return None
    return numerator / denominator


def percentage(part: Decimal, whole: Decimal) -> Decimal | None:
    ratio = safe_divide(part, whole)
    return None if ratio is None else quantize_percent(ratio * 100)


def apply_percent(base: Decimal, pct: Decimal) -> Decimal:
    """`base` adjusted by `pct` percent. Exact; the caller rounds."""
    return base * (Decimal(1) + pct / Decimal(100))


def format_inr(value: Decimal | None) -> str:
    """Indian grouping, for rendered output. Never used before a figure is final."""
    if value is None:
        return "—"
    quantised = quantize_money(value)
    sign = "-" if quantised < 0 else ""
    digits, _, fraction = str(abs(quantised)).partition(".")

    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups: list[str] = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join([*groups, tail])

    return f"{sign}₹{digits}.{fraction or '00'}"
