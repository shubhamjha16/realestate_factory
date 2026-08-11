"""
Sample adequacy.

A valuation is only as good as the evidence behind it, and there are four ways
the evidence can be inadequate in a way the arithmetic will not reveal:

  · **too few comparables** — two sales is an anecdote; the mean of two is not a
    market rate, and no amount of adjustment makes it one
  · **stale comparables** — a sale from four years ago says what the market was,
    not what it is, and a time adjustment large enough to bridge that gap is
    itself the dominant assumption in the valuation
  · **distant comparables** — a sale 40 km away is a different market
  · **a wide spread after adjustment** — this is the important one. If the
    adjusted rates still disagree sharply, the adjustments did not explain the
    differences, so the properties are not comparable and averaging them produces
    a figure with no support underneath it

Each raises and names what is wrong. None of them softens into a caveat in the
prose: a report that says "based on limited evidence" and then states a figure to
the rupee has not disclosed anything, it has hedged.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.configs.envConfig import settings
from app.services.valuation.adjust import AdjustedComparable, AdjustmentGrid

# Beyond this, the adjusted rates disagree too much for their mean to mean
# anything. Configurable because a homogeneous apartment block and a stretch of
# industrial land do not have the same natural dispersion.
DEFAULT_MAX_SPREAD_PCT = Decimal("25")


class ComparableEvidenceError(ValueError):
    """The evidence does not support a conclusion. Blocking, never advisory."""

    def __init__(self, message: str, *, code: str, detail: dict | None = None):
        self.code = code
        self.detail = detail or {}
        super().__init__(message)


@dataclass(frozen=True)
class AdequacyPolicy:
    min_sample: int
    max_age_months: int
    max_radius_m: int
    max_spread_pct: Decimal

    @classmethod
    def from_settings(cls) -> AdequacyPolicy:
        return cls(
            min_sample=settings.COMPARABLE_MIN_SAMPLE,
            max_age_months=settings.COMPARABLE_MAX_AGE_MONTHS,
            max_radius_m=settings.COMPARABLE_RADIUS_M,
            max_spread_pct=DEFAULT_MAX_SPREAD_PCT,
        )


def _months_between(earlier: date, later: date) -> int:
    return (later.year - earlier.year) * 12 + (later.month - earlier.month)


def validate_sample_size(count: int, policy: AdequacyPolicy) -> None:
    if count < policy.min_sample:
        raise ComparableEvidenceError(
            f"{count} comparable(s) is below the minimum of {policy.min_sample}. "
            f"A rate derived from fewer is not supported by the evidence, and no "
            f"adjustment makes it so — obtain more comparables or state the "
            f"valuation on a different basis.",
            code="insufficient_comparables",
            detail={"count": count, "minimum": policy.min_sample},
        )


def validate_ages(
    comparables: list[AdjustedComparable], valuation_date: date, policy: AdequacyPolicy
) -> None:
    stale = [
        c
        for c in comparables
        if c.sale_date and _months_between(c.sale_date, valuation_date) > policy.max_age_months
    ]
    if stale:
        named = ", ".join(
            f"{c.address} ({c.sale_date:%b %Y})" for c in stale if c.sale_date
        )
        raise ComparableEvidenceError(
            f"{len(stale)} comparable(s) are older than {policy.max_age_months} months "
            f"as at {valuation_date:%d %b %Y}: {named}. A time adjustment large enough "
            f"to bridge that gap becomes the dominant assumption in the valuation.",
            code="stale_comparables",
            detail={"stale": [c.address for c in stale], "max_age_months": policy.max_age_months},
        )


def validate_distances(
    distances_m: dict[str, Decimal | None], policy: AdequacyPolicy
) -> None:
    distant = {
        address: metres
        for address, metres in distances_m.items()
        if metres is not None and metres > policy.max_radius_m
    }
    if distant:
        named = ", ".join(f"{a} ({int(m)} m)" for a, m in distant.items())
        raise ComparableEvidenceError(
            f"{len(distant)} comparable(s) lie beyond {policy.max_radius_m} m: {named}. "
            f"A sale outside the locality is evidence of a different market.",
            code="distant_comparables",
            detail={"distant": list(distant), "max_radius_m": policy.max_radius_m},
        )


def validate_spread(grid: AdjustmentGrid, policy: AdequacyPolicy) -> None:
    """
    The blocking check S7 exists for.

    A wide spread *after* adjustment is not a rounding problem. It says the
    adjustments failed to explain why these sales differ — so the mean of them
    is a number with nothing underneath it.
    """
    spread = grid.spread_pct()
    if spread is None or spread <= policy.max_spread_pct:
        return

    outliers = grid.outliers(policy.max_spread_pct / 2)
    named = ", ".join(
        f"{c.address} (adjusted ₹{c.adjusted_rate}/sqft)" for c in outliers
    ) or "no single comparable dominates; the whole set disagrees"

    raise ComparableEvidenceError(
        f"the adjusted rates span {spread}%, beyond the {policy.max_spread_pct}% "
        f"threshold. After adjustment the comparables still disagree, which means "
        f"the adjustments did not explain the differences between them. "
        f"Responsible: {named}.",
        code="adjusted_spread_too_wide",
        detail={
            "spread_pct": str(spread),
            "threshold_pct": str(policy.max_spread_pct),
            "outliers": [c.address for c in outliers],
        },
    )


def validate_rationales(grid: AdjustmentGrid) -> None:
    """
    Belt and braces: `Adjustment` refuses to construct without a rationale, so
    this can only fire if a grid were assembled some other way. It exists because
    the day someone adds a second construction path is the day this matters.
    """
    missing = [
        f"{c.address}/{a.factor}"
        for c in grid.comparables
        for a in c.adjustments
        if not (a.rationale or "").strip()
    ]
    if missing:
        raise ComparableEvidenceError(
            f"adjustments without a written rationale: {', '.join(missing)}. "
            f"The grid is the report's defensibility; a percentage nobody explained "
            f"cannot be reviewed.",
            code="missing_rationale",
            detail={"missing": missing},
        )


def validate_grid(
    grid: AdjustmentGrid,
    *,
    valuation_date: date,
    distances_m: dict[str, Decimal | None] | None = None,
    policy: AdequacyPolicy | None = None,
) -> None:
    """
    Every check, in the order a reviewer would ask them.

    Sample size first: with two comparables the spread is meaningless, and
    reporting the spread before the count would bury the real problem.
    """
    policy = policy or AdequacyPolicy.from_settings()

    validate_sample_size(grid.count, policy)
    validate_rationales(grid)
    validate_ages(grid.comparables, valuation_date, policy)
    if distances_m:
        validate_distances(distances_m, policy)
    validate_spread(grid, policy)
