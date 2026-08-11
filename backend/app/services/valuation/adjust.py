"""
The comparable adjustment grid.

**This module is the valuation's defensibility.** Everything else in
`services/valuation/` computes something; this is the part a reviewer, a bank or
a tribunal actually asks to see, line by line.

The defect it closes: `analyse_comparables` took a trimmed mean of raw
price-per-sqft and called it `suggested_rate`. Actual practice adjusts each
comparable for the ways it differs from the subject — size, age, floor, frontage,
view, condition, transaction date, location, tenure and distress — before
averaging anything. An unadjusted mean is not a valuation, and a report that
presents one as though it were is the single largest professional exposure in
this repository.

Two design decisions worth stating:

**Order is fixed and it matters.** Adjustments compound multiplicatively, so
applying them in a different order than the report describes produces a different
number than the report explains. `ADJUSTMENT_ORDER` is that order: market-level
adjustments (time, location, tenure) first, because they restate the comparable
as though it had transacted here and now; then physical ones against the subject.

**Every adjustment carries a written rationale.** Not optional, not defaulted.
"+5% for floor" is a number; "+5% — subject is on the 6th floor against this
comparable's 2nd; the local market pays a premium above the podium" is evidence.
The grid without rationales is a spreadsheet, not a valuation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.services.valuation.money import (
    ZERO,
    quantize_percent,
    quantize_rate,
    safe_divide,
    to_decimal,
)

# The order adjustments are applied in. Market-level first: they restate the
# comparable as though it had transacted in this location, at this date, on this
# tenure. Physical differences are then measured against the subject.
ADJUSTMENT_ORDER: tuple[str, ...] = (
    "time",
    "location",
    "tenure",
    "size",
    "age",
    "floor",
    "frontage",
    "view",
    "condition",
    "distress",
)

ADJUSTMENT_FACTORS = frozenset(ADJUSTMENT_ORDER)

FACTOR_LABELS = {
    "time": "Transaction date",
    "location": "Location",
    "tenure": "Tenure",
    "size": "Size",
    "age": "Age",
    "floor": "Floor",
    "frontage": "Frontage",
    "view": "View",
    "condition": "Condition",
    "distress": "Distress",
}


class AdjustmentError(ValueError):
    """An adjustment that cannot be defended is refused rather than recorded."""


@dataclass(frozen=True)
class Adjustment:
    """
    One line of the grid.

    `pct` is signed and expressed against the comparable: +5 means the comparable
    is inferior to the subject on this factor and its rate is adjusted upward to
    stand in for it.
    """

    factor: str
    pct: Decimal
    rationale: str
    applied_by: str | None = None

    def __post_init__(self) -> None:
        if self.factor not in ADJUSTMENT_FACTORS:
            raise AdjustmentError(
                f"unknown adjustment factor {self.factor!r}; "
                f"expected one of {', '.join(ADJUSTMENT_ORDER)}"
            )
        if not (self.rationale or "").strip():
            raise AdjustmentError(
                f"the {self.factor} adjustment has no rationale. Every adjustment "
                f"carries a written reason — the grid is the report's defensibility, "
                f"and a percentage with no reason behind it cannot be reviewed."
            )
        # A single adjustment beyond half the value is not an adjustment, it is
        # a statement that the comparable is not comparable.
        if abs(self.pct) > 50:
            raise AdjustmentError(
                f"the {self.factor} adjustment is {self.pct}%. An adjustment beyond "
                f"±50% means the property is not a comparable; reject it instead."
            )


@dataclass(frozen=True)
class AdjustedComparable:
    comparable_id: str
    address: str
    sale_date: date | None
    sale_price: Decimal
    area_sqft: Decimal
    raw_rate: Decimal
    adjustments: tuple[Adjustment, ...]
    adjusted_rate: Decimal
    net_adjustment_pct: Decimal
    gross_adjustment_pct: Decimal

    @property
    def rationale_lines(self) -> list[str]:
        return [
            f"{FACTOR_LABELS[a.factor]}: {a.pct:+}% — {a.rationale}"
            for a in self.adjustments
        ]


def raw_rate(sale_price: Decimal, area_sqft: Decimal) -> Decimal:
    if area_sqft <= 0:
        raise AdjustmentError("a comparable with no area cannot produce a rate")
    return sale_price / area_sqft


def apply_adjustments(
    *,
    comparable_id: str,
    address: str,
    sale_price: Decimal | str,
    area_sqft: Decimal | str,
    adjustments: list[Adjustment],
    sale_date: date | None = None,
) -> AdjustedComparable:
    """
    Apply the grid to one comparable, in `ADJUSTMENT_ORDER`.

    Compounding, not additive. A +10% and a +10% is +21%, not +20% — each
    adjustment restates a rate that the previous one has already restated, and
    summing them understates the total on every comparable that needs more than
    one.
    """
    price = to_decimal(sale_price, field="sale_price")
    area = to_decimal(area_sqft, field="area_sqft")
    base = raw_rate(price, area)

    seen: set[str] = set()
    for adjustment in adjustments:
        if adjustment.factor in seen:
            raise AdjustmentError(
                f"two {adjustment.factor} adjustments on the same comparable. "
                f"Combine them into one line with one rationale, so the grid shows "
                f"what was actually applied."
            )
        seen.add(adjustment.factor)

    ordered = sorted(adjustments, key=lambda a: ADJUSTMENT_ORDER.index(a.factor))

    rate = base
    for adjustment in ordered:
        rate = rate * (Decimal(1) + adjustment.pct / Decimal(100))

    net = safe_divide(rate - base, base)
    net_pct = quantize_percent((net or ZERO) * 100)
    gross_pct = quantize_percent(sum((abs(a.pct) for a in ordered), ZERO))

    return AdjustedComparable(
        comparable_id=comparable_id,
        address=address,
        sale_date=sale_date,
        sale_price=price,
        area_sqft=area,
        raw_rate=quantize_rate(base),
        adjustments=tuple(ordered),
        adjusted_rate=quantize_rate(rate),
        net_adjustment_pct=net_pct,
        gross_adjustment_pct=gross_pct,
    )


@dataclass
class AdjustmentGrid:
    """
    The whole grid, and the statistics a reviewer reads off it.

    `gross_adjustment_pct` matters as much as the net. A comparable adjusted
    +15% and −15% nets to zero but has been moved 30% in total, and a set whose
    gross adjustments are large is a set that was not very comparable to begin
    with — which is a conclusion about the evidence, not about the property.
    """

    comparables: list[AdjustedComparable] = field(default_factory=list)

    @property
    def adjusted_rates(self) -> list[Decimal]:
        return [c.adjusted_rate for c in self.comparables]

    @property
    def count(self) -> int:
        return len(self.comparables)

    def mean_adjusted_rate(self) -> Decimal | None:
        if not self.comparables:
            return None
        return quantize_rate(sum(self.adjusted_rates, ZERO) / Decimal(self.count))

    def median_adjusted_rate(self) -> Decimal | None:
        if not self.comparables:
            return None
        ordered = sorted(self.adjusted_rates)
        mid = self.count // 2
        if self.count % 2:
            return quantize_rate(ordered[mid])
        return quantize_rate((ordered[mid - 1] + ordered[mid]) / Decimal(2))

    def spread_pct(self) -> Decimal | None:
        """
        How far the adjusted rates span, against their mean.

        The number S7's validator blocks on. A wide spread after adjustment means
        the adjustments did not explain the differences — so the comparables are
        not comparable, and averaging them produces a figure with no support.
        """
        if self.count < 2:
            return None
        rates = self.adjusted_rates
        mean = sum(rates, ZERO) / Decimal(self.count)
        if mean == 0:
            return None
        return quantize_percent((max(rates) - min(rates)) / mean * 100)

    def outliers(self, threshold_pct: Decimal) -> list[AdjustedComparable]:
        """Which comparables are responsible for a spread — named, not just counted."""
        if self.count < 2:
            return []
        mean = sum(self.adjusted_rates, ZERO) / Decimal(self.count)
        if mean == 0:
            return []
        return [
            c
            for c in self.comparables
            if abs((c.adjusted_rate - mean) / mean * 100) > threshold_pct
        ]

    def mean_gross_adjustment_pct(self) -> Decimal | None:
        if not self.comparables:
            return None
        return quantize_percent(
            sum((c.gross_adjustment_pct for c in self.comparables), ZERO) / Decimal(self.count)
        )

    def to_dict(self) -> dict:
        return {
            "count": self.count,
            "mean_adjusted_rate": str(self.mean_adjusted_rate() or ""),
            "median_adjusted_rate": str(self.median_adjusted_rate() or ""),
            "spread_pct": str(self.spread_pct() or ""),
            "mean_gross_adjustment_pct": str(self.mean_gross_adjustment_pct() or ""),
            "comparables": [
                {
                    "id": c.comparable_id,
                    "address": c.address,
                    "sale_date": c.sale_date.isoformat() if c.sale_date else None,
                    "sale_price": str(c.sale_price),
                    "area_sqft": str(c.area_sqft),
                    "raw_rate": str(c.raw_rate),
                    "adjusted_rate": str(c.adjusted_rate),
                    "net_adjustment_pct": str(c.net_adjustment_pct),
                    "gross_adjustment_pct": str(c.gross_adjustment_pct),
                    "adjustments": [
                        {
                            "factor": a.factor,
                            "label": FACTOR_LABELS[a.factor],
                            "pct": str(a.pct),
                            "rationale": a.rationale,
                        }
                        for a in c.adjustments
                    ],
                }
                for c in self.comparables
            ],
        }


def build_grid(entries: list[dict]) -> AdjustmentGrid:
    """
    Build a grid from the shape the API and the parser produce.

    Each entry: id, address, sale_price, area_sqft, sale_date, and a list of
    `{factor, pct, rationale}`.
    """
    grid = AdjustmentGrid()
    for entry in entries:
        adjustments = [
            Adjustment(
                factor=a["factor"],
                pct=to_decimal(a["pct"], field=f"{a['factor']} pct"),
                rationale=a.get("rationale", ""),
                applied_by=a.get("applied_by"),
            )
            for a in entry.get("adjustments", [])
        ]
        grid.comparables.append(
            apply_adjustments(
                comparable_id=str(entry.get("id") or entry.get("address", "")),
                address=str(entry.get("address", "")),
                sale_price=entry["sale_price"],
                area_sqft=entry["area_sqft"],
                sale_date=entry.get("sale_date"),
                adjustments=adjustments,
            )
        )
    return grid
