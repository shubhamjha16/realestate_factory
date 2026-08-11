"""
The cost approach — replacement cost less depreciation, plus land.

The approach a bank asks for on a specialised building nobody sells and nobody
lets: a factory, a hospital, a school. It is also the one most often done badly,
because "less depreciation" quietly does most of the work and is frequently a
single unexplained percentage.

So depreciation is decomposed here into its three recognised causes, each stated
separately:

  · **physical** — wear, age against economic life. Arithmetic.
  · **functional** — the building is worth less than its cost because of how it
    was built: ceiling heights, layout, services nobody specifies any more.
  · **external** — nothing to do with the building. The road moved, the industry
    left. Also called economic obsolescence.

A single blended figure hides which of the three is being claimed, and they are
not equally defensible: physical depreciation is computable, the other two are
judgements that need a reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.services.valuation.money import (
    ZERO,
    quantize_money,
    quantize_percent,
    to_decimal,
)


class CostApproachError(ValueError):
    """A cost valuation that cannot be defended is refused rather than computed."""


@dataclass(frozen=True)
class Depreciation:
    physical_pct: Decimal
    functional_pct: Decimal = ZERO
    external_pct: Decimal = ZERO
    functional_rationale: str = ""
    external_rationale: str = ""

    def __post_init__(self) -> None:
        for pct, name, why in (
            (self.functional_pct, "functional", self.functional_rationale),
            (self.external_pct, "external", self.external_rationale),
        ):
            if pct > 0 and not why.strip():
                raise CostApproachError(
                    f"{pct}% of {name} obsolescence with no rationale. Physical "
                    f"depreciation is arithmetic; {name} obsolescence is a judgement, "
                    f"and a judgement with no reason cannot be reviewed."
                )
        for pct, name in (
            (self.physical_pct, "physical"),
            (self.functional_pct, "functional"),
            (self.external_pct, "external"),
        ):
            if not (0 <= pct <= 100):
                raise CostApproachError(f"{name} depreciation of {pct}% is outside 0–100%")

    @property
    def total_pct(self) -> Decimal:
        """
        Compounding, not additive.

        Three separate 20% deductions leave 51.2% of the cost standing, not 40%.
        Each applies to what the previous one left, because a building already
        half worn does not lose another fifth *of its original cost* to a
        functional defect.
        """
        remaining = Decimal(1)
        for pct in (self.physical_pct, self.functional_pct, self.external_pct):
            remaining *= Decimal(1) - pct / Decimal(100)
        return quantize_percent((Decimal(1) - remaining) * 100)

    def to_dict(self) -> dict:
        return {
            "physical_pct": str(quantize_percent(self.physical_pct)),
            "functional_pct": str(quantize_percent(self.functional_pct)),
            "functional_rationale": self.functional_rationale,
            "external_pct": str(quantize_percent(self.external_pct)),
            "external_rationale": self.external_rationale,
            "total_pct": str(self.total_pct),
            "basis": "compounding: each cause applies to what the previous one left",
        }


def straight_line_physical(age_years: int, economic_life_years: int) -> Decimal:
    """
    Age over economic life, capped at 100%.

    The simplest defensible method, and the one a reviewer expects unless the
    report says otherwise. A building past its economic life is not worth less
    than nothing — it retains scrap and site value, which the land component
    carries.
    """
    if economic_life_years <= 0:
        raise CostApproachError("economic life must be greater than zero years")
    if age_years < 0:
        raise CostApproachError("age cannot be negative")
    ratio = Decimal(min(age_years, economic_life_years)) / Decimal(economic_life_years)
    return quantize_percent(ratio * 100)


@dataclass(frozen=True)
class CostApproachResult:
    land_value: Decimal
    replacement_cost_new: Decimal
    depreciation: Depreciation
    depreciated_building_value: Decimal
    indicated_value: Decimal
    rationale: str

    def to_dict(self) -> dict:
        return {
            "method": "cost",
            "land_value": str(self.land_value),
            "replacement_cost_new": str(self.replacement_cost_new),
            "depreciation": self.depreciation.to_dict(),
            "depreciated_building_value": str(self.depreciated_building_value),
            "indicated_value": str(self.indicated_value),
            "rationale": self.rationale,
        }


def value(
    *,
    land_value: Decimal | str,
    built_up_area_sqft: Decimal | str,
    replacement_cost_per_sqft: Decimal | str,
    depreciation: Depreciation,
    rationale: str,
) -> CostApproachResult:
    """
    Land value plus depreciated replacement cost of the improvements.

    Land is **not** depreciated. It is a common error and it understates the
    answer badly on an old building: the structure wears out, the site does not.
    """
    land = to_decimal(land_value, field="land_value")
    area = to_decimal(built_up_area_sqft, field="built_up_area_sqft")
    rate = to_decimal(replacement_cost_per_sqft, field="replacement_cost_per_sqft")

    if land < 0:
        raise CostApproachError("land value cannot be negative")
    if area <= 0:
        raise CostApproachError("built-up area must be greater than zero")
    if rate <= 0:
        raise CostApproachError("replacement cost per sq ft must be greater than zero")
    if not (rationale or "").strip():
        raise CostApproachError(
            "the cost approach has no rationale. State the source of the replacement "
            "cost rate and the economic life assumed — both are judgements a "
            "reviewer must be able to check."
        )

    replacement_new = area * rate
    remaining = Decimal(1) - depreciation.total_pct / Decimal(100)
    depreciated = replacement_new * remaining

    return CostApproachResult(
        land_value=quantize_money(land),
        replacement_cost_new=quantize_money(replacement_new),
        depreciation=depreciation,
        depreciated_building_value=quantize_money(depreciated),
        # Land is not depreciated: the structure wears out, the site does not.
        indicated_value=quantize_money(land + depreciated),
        rationale=rationale,
    )
