"""
The sales comparison approach.

Built on the adjustment grid, not on a mean of raw rates.

The prototype's `analyse_comparables` returned `suggested_rate` — a trimmed mean
of unadjusted price-per-sqft — and the report presented it as a value conclusion.
That is the defect S7 exists to close. The trimmed mean survives here, under a
name that says what it is: a **pre-adjustment sanity statistic**, useful for
noticing that a comparable set is wild before anyone spends an hour adjusting it,
and never a conclusion.

The conclusion comes from `concluded_rate`, which is the central tendency of the
*adjusted* rates. The median is preferred over the mean where the set is small,
because one comparable that survived adjustment badly should not drag the
conclusion — and with five comparables it can move a mean by several per cent.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.services.valuation.adjust import AdjustmentGrid
from app.services.valuation.money import (
    ZERO,
    quantize_money,
    quantize_percent,
    quantize_rate,
    to_decimal,
)

# Below this, the mean is too easily moved by one comparable and the median is
# the more honest central tendency.
SMALL_SAMPLE = 6


@dataclass(frozen=True)
class PreAdjustmentStats:
    """
    What the raw, unadjusted rates look like.

    Reported so a reviewer can see the effect of the grid — and, in the report,
    so the adjustment work is visible rather than implied. **Not a conclusion.**
    """

    count: int
    mean_rate: Decimal
    trimmed_mean_rate: Decimal
    min_rate: Decimal
    max_rate: Decimal
    spread_pct: Decimal | None

    def to_dict(self) -> dict:
        return {
            "count": self.count,
            "mean_rate": str(self.mean_rate),
            # Named for what it is. It is not `suggested_rate` and never will be.
            "trimmed_mean_rate_sanity_only": str(self.trimmed_mean_rate),
            "min_rate": str(self.min_rate),
            "max_rate": str(self.max_rate),
            "spread_pct": str(self.spread_pct) if self.spread_pct is not None else None,
        }


def pre_adjustment_stats(raw_rates: list[Decimal]) -> PreAdjustmentStats | None:
    """
    Trimmed mean over the raw rates — the prototype's outlier handling, kept.

    It was one of the two best decisions in the original code and it still earns
    its place: a set whose raw trimmed mean is wildly off its plain mean is a set
    with a data problem, and that is worth knowing before adjusting anything.
    """
    if not raw_rates:
        return None

    ordered = sorted(raw_rates)
    n = len(ordered)
    mean = sum(ordered, ZERO) / Decimal(n)

    trim = max(1, int(n * 0.1))
    trimmed = ordered[trim : n - trim] if n > 4 else ordered
    trimmed_mean = sum(trimmed, ZERO) / Decimal(len(trimmed)) if trimmed else mean

    spread = (
        quantize_percent((ordered[-1] - ordered[0]) / mean * 100) if mean else None
    )

    return PreAdjustmentStats(
        count=n,
        mean_rate=quantize_rate(mean),
        trimmed_mean_rate=quantize_rate(trimmed_mean),
        min_rate=quantize_rate(ordered[0]),
        max_rate=quantize_rate(ordered[-1]),
        spread_pct=spread,
    )


@dataclass(frozen=True)
class SalesComparisonResult:
    concluded_rate: Decimal
    basis: str
    indicated_value: Decimal
    subject_area_sqft: Decimal
    grid: AdjustmentGrid
    pre_adjustment: PreAdjustmentStats | None
    value_range_low: Decimal
    value_range_high: Decimal

    def to_dict(self) -> dict:
        return {
            "method": "sales",
            "concluded_rate": str(self.concluded_rate),
            "concluded_rate_basis": self.basis,
            "subject_area_sqft": str(self.subject_area_sqft),
            "indicated_value": str(self.indicated_value),
            "value_range_low": str(self.value_range_low),
            "value_range_high": str(self.value_range_high),
            "adjustment_grid": self.grid.to_dict(),
            "pre_adjustment": self.pre_adjustment.to_dict() if self.pre_adjustment else None,
        }


def conclude(
    grid: AdjustmentGrid,
    *,
    subject_area_sqft: Decimal | str,
    valuation_date: date | None = None,
) -> SalesComparisonResult:
    """
    Reduce the grid to one rate and one value.

    The range is the adjusted rates' own span, not a percentage bracket invented
    around the conclusion. A range that comes from the evidence tells a reader
    what the evidence actually supports; ±10% tells them nothing.
    """
    if grid.count == 0:
        raise ValueError("cannot conclude a sales comparison from an empty grid")

    area = to_decimal(subject_area_sqft, field="subject_area_sqft")
    if area <= 0:
        raise ValueError("the subject's area must be greater than zero")

    use_median = grid.count < SMALL_SAMPLE
    rate = grid.median_adjusted_rate() if use_median else grid.mean_adjusted_rate()
    assert rate is not None  # count > 0 guarantees it

    basis = (
        f"median of {grid.count} adjusted rates (small sample: the mean is too "
        f"easily moved by one comparable)"
        if use_median
        else f"mean of {grid.count} adjusted rates"
    )

    rates = grid.adjusted_rates
    raw_rates = [c.raw_rate for c in grid.comparables]

    return SalesComparisonResult(
        concluded_rate=quantize_rate(rate),
        basis=basis,
        indicated_value=quantize_money(rate * area),
        subject_area_sqft=area,
        grid=grid,
        pre_adjustment=pre_adjustment_stats(raw_rates),
        value_range_low=quantize_money(min(rates) * area),
        value_range_high=quantize_money(max(rates) * area),
    )
