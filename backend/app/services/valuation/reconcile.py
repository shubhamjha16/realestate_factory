"""
Reconciliation — the step that produces a defensible final figure.

Three approaches produce three numbers. Reconciliation is where a valuer says
which of them they believe and why. It is **not** an average: averaging
approaches blindly is how a report ends up with a figure no approach supports and
nobody would defend.

Two rules, both enforced rather than requested:

  · **The weights sum to 1.** Not 0.99, not 1.01. Weights that do not sum are
    not weights, and the "conclusion" they produce is not the weighted value of
    anything.
  · **Every weight carries a rationale.** A 70% weight on comparable sales is a
    professional judgement about which evidence is better here. Stating the
    weight without the reason states a conclusion without its reasoning, and the
    reasoning is what a reviewer is checking.

The mandate's basis and purpose determine which approaches are mandatory, so a
conclusion that skips one is refused — see `configs/valuationPolicy.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.configs.valuationPolicy import (
    ALL_METHODS,
    INCOME,
    ApproachPolicy,
    policy_for,
)
from app.services.valuation.money import (
    ZERO,
    percentage,
    quantize_money,
    quantize_percent,
    to_decimal,
)

# Weights are decimals summing to 1. A tolerance exists only for representation,
# not for sloppiness: 0.333 + 0.333 + 0.334 is fine, 0.3 + 0.3 + 0.3 is not.
WEIGHT_TOLERANCE = Decimal("0.0001")

# Beyond this, the approaches disagree so much that a weighted average of them is
# a number no approach supports.
DEFAULT_MAX_DIVERGENCE_PCT = Decimal("30")


class ReconciliationError(ValueError):
    def __init__(self, message: str, *, code: str, detail: dict | None = None):
        self.code = code
        self.detail = detail or {}
        super().__init__(message)


@dataclass(frozen=True)
class ApproachInput:
    method: str
    indicated_value: Decimal
    weight: Decimal
    rationale: str
    inputs: dict | None = None

    def __post_init__(self) -> None:
        if self.method not in ALL_METHODS:
            raise ReconciliationError(
                f"unknown method {self.method!r}; expected one of {', '.join(ALL_METHODS)}",
                code="unknown_method",
            )
        if not (self.rationale or "").strip():
            raise ReconciliationError(
                f"the {self.method} approach carries a weight of {self.weight} with no "
                f"rationale. A weight is a judgement about which evidence is better "
                f"here, and a judgement with no reason cannot be reviewed.",
                code="missing_weight_rationale",
                detail={"method": self.method},
            )
        if not (ZERO <= self.weight <= Decimal(1)):
            raise ReconciliationError(
                f"a weight of {self.weight} on the {self.method} approach is outside 0–1",
                code="weight_out_of_range",
                detail={"method": self.method, "weight": str(self.weight)},
            )


@dataclass(frozen=True)
class Reconciliation:
    concluded_value: Decimal
    approaches: tuple[ApproachInput, ...]
    value_range_low: Decimal
    value_range_high: Decimal
    divergence_pct: Decimal | None
    basis: str
    premise: str

    def to_dict(self) -> dict:
        return {
            "concluded_value": str(self.concluded_value),
            "basis": self.basis,
            "premise": self.premise,
            "value_range_low": str(self.value_range_low),
            "value_range_high": str(self.value_range_high),
            "divergence_pct": str(self.divergence_pct) if self.divergence_pct is not None else None,
            "approaches": [
                {
                    "method": a.method,
                    "indicated_value": str(a.indicated_value),
                    "weight": str(a.weight),
                    "weight_pct": str(quantize_percent(a.weight * 100)),
                    "rationale": a.rationale,
                    "inputs": a.inputs or {},
                }
                for a in self.approaches
            ],
        }

    def narrative(self) -> str:
        """
        What the report's reconciliation section says.

        Generated from the figures rather than drafted, because this paragraph is
        the one a reviewer checks against the numbers — and a model that writes
        it from scratch is a model inventing a figure (S11).
        """
        lines = [
            f"The approaches indicate values between "
            f"{self.value_range_low} and {self.value_range_high}."
        ]
        for a in self.approaches:
            if a.weight == 0:
                lines.append(
                    f"The {a.method} approach is not relied upon: {a.rationale}"
                )
            else:
                lines.append(
                    f"The {a.method} approach indicates {a.indicated_value} and is "
                    f"weighted {quantize_percent(a.weight * 100)}%: {a.rationale}"
                )
        lines.append(f"The value concluded on this evidence is {self.concluded_value}.")
        return " ".join(lines)


def validate_weights(approaches: list[ApproachInput]) -> None:
    if not approaches:
        raise ReconciliationError(
            "a reconciliation needs at least one approach", code="no_approaches"
        )

    seen = [a.method for a in approaches]
    duplicates = {m for m in seen if seen.count(m) > 1}
    if duplicates:
        raise ReconciliationError(
            f"the {', '.join(sorted(duplicates))} approach appears twice. Combine them "
            f"into one weighted line, so the reconciliation shows what was applied.",
            code="duplicate_method",
        )

    total = sum((a.weight for a in approaches), ZERO)
    if abs(total - Decimal(1)) > WEIGHT_TOLERANCE:
        raise ReconciliationError(
            f"the weights sum to {total}, not 1. Weights that do not sum to 1 are not "
            f"weights, and the figure they produce is not the weighted value of "
            f"anything.",
            code="weights_do_not_sum",
            detail={
                "sum": str(total),
                "weights": {a.method: str(a.weight) for a in approaches},
            },
        )


def validate_policy(
    approaches: list[ApproachInput], policy: ApproachPolicy
) -> None:
    """
    The mandate's basis and purpose decide what the report must include.

    An approach present with zero weight does not satisfy a requirement: showing
    a number and then declining to rely on it is not the same as valuing on that
    basis, and a lender asking for a yield is not answered by one that was
    computed and ignored.
    """
    relied_on = {a.method for a in approaches if a.weight > 0}

    missing = [m for m in policy.required if m not in relied_on]
    if missing:
        raise ReconciliationError(
            f"this mandate requires the {', '.join(missing)} approach, and the "
            f"conclusion does not rely on it. {policy.note}",
            code="required_approach_missing",
            detail={"missing": missing, "relied_on": sorted(relied_on)},
        )

    forbidden = [m for m in policy.forbidden if m in relied_on]
    if forbidden:
        raise ReconciliationError(
            f"this basis of value excludes the {', '.join(forbidden)} approach, and "
            f"the conclusion relies on it. {policy.note}",
            code="forbidden_approach_used",
            detail={"forbidden": forbidden},
        )


def validate_divergence(
    approaches: list[ApproachInput], max_divergence_pct: Decimal
) -> None:
    """
    If the approaches disagree wildly, weighting them is not reconciliation.

    Two methods that differ by half say one of them is wrong, and the answer is
    to find out which — not to split the difference and present the midpoint as
    though it were supported.
    """
    relied_on = [a.indicated_value for a in approaches if a.weight > 0]
    if len(relied_on) < 2:
        return

    low, high = min(relied_on), max(relied_on)
    if low <= 0:
        return
    divergence = percentage(high - low, low)
    if divergence is not None and divergence > max_divergence_pct:
        raise ReconciliationError(
            f"the relied-upon approaches diverge by {divergence}%, beyond the "
            f"{max_divergence_pct}% threshold ({low} to {high}). Two methods that "
            f"disagree by this much say one of them is wrong; weighting them "
            f"produces a figure neither supports.",
            code="approaches_diverge",
            detail={
                "divergence_pct": str(divergence),
                "low": str(low),
                "high": str(high),
            },
        )


def reconcile(
    approaches: list[ApproachInput],
    *,
    basis: str = "market",
    premise: str = "existing_use",
    income_producing: bool = False,
    specialised: bool = False,
    purpose: str | None = None,
    max_divergence_pct: Decimal | None = None,
) -> Reconciliation:
    """
    Weight the approaches into one figure, or refuse.

    Every check runs before anything is computed: a conclusion is not produced
    and then validated, because a figure that exists is a figure someone will
    quote.
    """
    policy = policy_for(basis, income_producing=income_producing, specialised=specialised)

    # A purpose can add a requirement the basis alone would not impose.
    if purpose and income_producing:
        from app.configs.valuationPolicy import PURPOSES_REQUIRING_INCOME

        if purpose in PURPOSES_REQUIRING_INCOME and INCOME not in policy.required:
            policy = ApproachPolicy(
                required=(*policy.required, INCOME),
                forbidden=policy.forbidden,
                note=(
                    f"{policy.note} A mandate instructed for {purpose} on an "
                    f"income-producing property requires the income approach."
                ),
            )

    validate_weights(approaches)
    validate_policy(approaches, policy)
    validate_divergence(approaches, max_divergence_pct or DEFAULT_MAX_DIVERGENCE_PCT)

    concluded = sum(
        (a.indicated_value * a.weight for a in approaches), ZERO
    )
    indicated = [a.indicated_value for a in approaches if a.weight > 0]

    return Reconciliation(
        concluded_value=quantize_money(concluded),
        approaches=tuple(approaches),
        value_range_low=quantize_money(min(indicated)),
        value_range_high=quantize_money(max(indicated)),
        divergence_pct=percentage(max(indicated) - min(indicated), min(indicated))
        if len(indicated) > 1 and min(indicated) > 0
        else None,
        basis=basis,
        premise=premise,
    )


def build(entries: list[dict], **kwargs) -> Reconciliation:
    """Reconcile from the shape the API accepts."""
    return reconcile(
        [
            ApproachInput(
                method=e["method"],
                indicated_value=to_decimal(e["indicated_value"], field="indicated_value"),
                weight=to_decimal(e["weight"], field="weight"),
                rationale=e.get("rationale", ""),
                inputs=e.get("inputs"),
            )
            for e in entries
        ],
        **kwargs,
    )
