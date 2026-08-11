"""
S9's exit proofs — three approaches and their reconciliation.

The worked case is a tenanted commercial property: Ardhika Square, Hosur Road,
Bengaluru. 16,315 sq ft chargeable, ₹2,381,750 a month contracted, built 2014 on
land worth ₹9 crore. It is valued three ways and reconciled to one figure with a
written rationale per weight — which is S9's central exit proof.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.configs.valuationPolicy import policy_for
from app.services.valuation.costApproach import (
    CostApproachError,
    Depreciation,
    straight_line_physical,
)
from app.services.valuation.costApproach import value as cost_value
from app.services.valuation.incomeApproach import (
    IncomeApproachError,
    OperatingStatement,
    direct_capitalisation,
    discounted_cash_flow,
    implied_cap_rate,
)
from app.services.valuation.reconcile import (
    ApproachInput,
    ReconciliationError,
    reconcile,
)

# Ardhika Square, as at 30 June 2026.
GROSS_ANNUAL_RENT = Decimal("28581000")     # ₹2,381,750 × 12
STATEMENT = OperatingStatement(
    gross_rent=GROSS_ANNUAL_RENT,
    vacancy_pct=Decimal("8"),               # two of eight units vacant
    opex_pct=Decimal("18"),
    other_income=Decimal("420000"),         # parking and signage
    non_recoverable=Decimal("310000"),
)


# ── income ────────────────────────────────────────────────────────────────────


def test_the_operating_statement_shows_every_deduction():
    """
    A reviewer checking a cap rate needs to see which deductions were made and
    at what level: 7% against 8% on ₹1 crore of NOI is ₹1.8 crore of value.
    """
    payload = STATEMENT.to_dict()
    assert Decimal(payload["effective_gross_income"]) == Decimal("26714520.00")
    assert Decimal(payload["net_operating_income"]) < Decimal(payload["effective_gross_income"])
    assert set(payload) >= {
        "gross_rent", "vacancy_pct", "other_income", "effective_gross_income",
        "opex_pct", "non_recoverable", "operating_expenses", "net_operating_income",
    }


def test_direct_capitalisation_produces_an_indicated_value():
    result = direct_capitalisation(
        STATEMENT,
        cap_rate_pct="8.25",
        rationale=(
            "Derived from three investment sales on Hosur Road transacting between "
            "8.0% and 8.6% in the twelve months to the valuation date, adjusted for "
            "the subject's shorter weighted unexpired term."
        ),
    )
    assert result.indicated_value > 0
    # NOI ÷ rate, to the rupee.
    expected = STATEMENT.net_operating_income / (Decimal("8.25") / 100)
    assert result.indicated_value == expected.quantize(Decimal("0.01"))
    assert result.cap_rate_pct == Decimal("8.2500")


def test_a_capitalisation_rate_without_a_rationale_is_refused():
    """The most consequential judgement in the approach, so it carries a reason."""
    with pytest.raises(IncomeApproachError, match="no rationale"):
        direct_capitalisation(STATEMENT, cap_rate_pct="8.25", rationale="  ")


def test_a_zero_capitalisation_rate_is_refused():
    with pytest.raises(IncomeApproachError, match="not usable"):
        direct_capitalisation(STATEMENT, cap_rate_pct="0", rationale="x")


def test_a_property_with_no_net_income_cannot_be_valued_on_income():
    loss_making = OperatingStatement(
        gross_rent=Decimal("1000000"), vacancy_pct=Decimal("50"),
        opex_pct=Decimal("120"), non_recoverable=Decimal("500000"),
    )
    with pytest.raises(IncomeApproachError, match="no net income"):
        direct_capitalisation(loss_making, cap_rate_pct="8", rationale="x")


def test_the_dcf_returns_its_workings_and_says_what_the_terminal_value_is_worth():
    """
    The terminal value usually dominates. A DCF whose workings are not visible is
    an assertion with arithmetic attached.
    """
    result = discounted_cash_flow(
        STATEMENT,
        discount_rate_pct="12",
        growth_pct="5",
        exit_cap_rate_pct="9",
        years=5,
        rationale="Discount rate from the weighted cost of capital for this asset class.",
    )
    assert result.indicated_value > 0
    assert len(result.cash_flows) == 6           # five years plus the terminal line
    assert "terminal" in str(result.cash_flows[-1]["year"])
    assert "% of the total" in result.rationale
    for flow in result.cash_flows[:5]:
        assert Decimal(flow["present_value"]) > 0


def test_the_dcf_refuses_a_zero_exit_yield():
    with pytest.raises(IncomeApproachError, match="exit capitalisation rate"):
        discounted_cash_flow(
            STATEMENT, discount_rate_pct="12", growth_pct="5",
            exit_cap_rate_pct="0", years=5, rationale="x",
        )


def test_implied_cap_rate_is_a_cross_check():
    assert implied_cap_rate("8000000", "100000000") == Decimal("8.0000")


# ── cost ──────────────────────────────────────────────────────────────────────


def test_straight_line_physical_depreciation():
    assert straight_line_physical(12, 60) == Decimal("20.0000")
    # Past its economic life, the building is fully depreciated — not negative.
    assert straight_line_physical(80, 60) == Decimal("100.0000")


def test_depreciation_compounds_across_its_three_causes():
    """
    Three 20% deductions leave 51.2% standing, not 40%. Each applies to what the
    previous one left.
    """
    depreciation = Depreciation(
        physical_pct=Decimal("20"),
        functional_pct=Decimal("20"),
        external_pct=Decimal("20"),
        functional_rationale="Ceiling heights below current specification for office use.",
        external_rationale="The arterial road realignment moved through traffic away.",
    )
    assert depreciation.total_pct == Decimal("48.8000")


def test_obsolescence_without_a_rationale_is_refused():
    """
    Physical depreciation is arithmetic. Functional and external are judgements,
    and they are where a single unexplained percentage does most of the work.
    """
    with pytest.raises(CostApproachError, match="functional obsolescence with no rationale"):
        Depreciation(physical_pct=Decimal("20"), functional_pct=Decimal("15"))


def test_the_cost_approach_does_not_depreciate_the_land():
    """A common error, and it understates an old building badly."""
    result = cost_value(
        land_value="90000000",
        built_up_area_sqft="16315",
        replacement_cost_per_sqft="2800",
        depreciation=Depreciation(physical_pct=straight_line_physical(12, 60)),
        rationale=(
            "Replacement cost from the CPWD plinth area rates for 2026 adjusted to "
            "Bengaluru; economic life of 60 years for RCC framed construction."
        ),
    )
    assert result.land_value == Decimal("90000000.00")
    assert result.replacement_cost_new == Decimal("45682000.00")
    # 20% physical depreciation on the building only.
    assert result.depreciated_building_value == Decimal("36545600.00")
    assert result.indicated_value == Decimal("126545600.00")


def test_the_cost_approach_needs_a_rationale():
    with pytest.raises(CostApproachError, match="no rationale"):
        cost_value(
            land_value="1", built_up_area_sqft="1", replacement_cost_per_sqft="1",
            depreciation=Depreciation(physical_pct=Decimal("0")), rationale="",
        )


# ── reconciliation: the central exit proof ────────────────────────────────────


def _three_approaches() -> list[ApproachInput]:
    income = direct_capitalisation(
        STATEMENT,
        cap_rate_pct="8.25",
        rationale="Three investment sales on Hosur Road at 8.0–8.6%.",
    )
    cost = cost_value(
        # Land at the Hosur Road guidance rate for a 0.6-acre commercial plot.
        land_value="190000000",
        built_up_area_sqft="16315",
        replacement_cost_per_sqft="2800",
        depreciation=Depreciation(physical_pct=straight_line_physical(12, 60)),
        rationale="CPWD plinth area rates for 2026; 60-year economic life.",
    )
    return [
        ApproachInput(
            method="sales",
            indicated_value=Decimal("240000000"),
            weight=Decimal("0.25"),
            rationale=(
                "Four strata sales in comparable buildings, but all of vacant floors; "
                "they do not price the covenant the subject's income carries."
            ),
        ),
        ApproachInput(
            method="income",
            indicated_value=income.indicated_value,
            weight=Decimal("0.60"),
            rationale=(
                "The subject is fully income-producing on institutional covenants. "
                "What a buyer purchases here is the income stream, so this approach "
                "carries the most weight."
            ),
            inputs=income.to_dict(),
        ),
        ApproachInput(
            method="cost",
            indicated_value=cost.indicated_value,
            weight=Decimal("0.15"),
            rationale=(
                "A cross-check only. The building is not specialised and a buyer in "
                "this market does not price it on reinstatement."
            ),
            inputs=cost.to_dict(),
        ),
    ]


def test_a_tenanted_commercial_property_is_valued_three_ways_and_reconciled(capsys):
    """
    S9's central exit proof: one figure, with a written rationale per weight.
    """
    result = reconcile(
        _three_approaches(),
        basis="market",
        premise="existing_use",
        income_producing=True,
        purpose="loan",
    )

    with capsys.disabled():
        print("\n  ── S9: Ardhika Square, three approaches ────────────────────")
        for a in result.approaches:
            print(f"  {a.method:<7} ₹{a.indicated_value:>16,}  weight {a.weight}")
        print(f"  {'range':<7} ₹{result.value_range_low:>16,} to ₹{result.value_range_high:,}")
        print(f"  {'diverge':<7} {result.divergence_pct}%")
        print(f"  {'CONCLUDED':<7} ₹{result.concluded_value:>16,}")
        print("  ────────────────────────────────────────────────────────────")

    assert result.value_range_low <= result.concluded_value <= result.value_range_high
    assert len(result.approaches) == 3
    assert all(a.rationale.strip() for a in result.approaches)

    # The narrative is generated from the figures, not drafted by a model.
    narrative = result.narrative()
    assert str(result.concluded_value) in narrative
    assert "weighted 60" in narrative


def test_weights_that_do_not_sum_to_one_are_refused():
    """S9's exit proof. 0.3 + 0.3 + 0.3 is not a set of weights."""
    approaches = _three_approaches()
    broken = [
        ApproachInput(a.method, a.indicated_value, Decimal("0.3"), a.rationale)
        for a in approaches
    ]
    with pytest.raises(ReconciliationError) as excinfo:
        reconcile(broken, income_producing=True)

    assert excinfo.value.code == "weights_do_not_sum"
    assert "sum to 0.9" in str(excinfo.value)
    assert "not the weighted value of anything" in str(excinfo.value)


def test_representation_is_tolerated_but_sloppiness_is_not():
    thirds = [
        ApproachInput("sales", Decimal("100"), Decimal("0.333"), "a"),
        ApproachInput("income", Decimal("100"), Decimal("0.333"), "b"),
        ApproachInput("cost", Decimal("100"), Decimal("0.334"), "c"),
    ]
    reconcile(thirds, income_producing=True)


def test_a_weight_without_a_rationale_is_refused():
    with pytest.raises(ReconciliationError, match="no rationale"):
        ApproachInput("sales", Decimal("1000"), Decimal("1"), "   ")


def test_a_mandate_requiring_the_income_approach_cannot_conclude_on_sales_alone():
    """
    S9's exit proof. A lender's credit note asks for the yield, and it is not
    answered by an approach that was computed and then ignored.
    """
    sales_only = [
        ApproachInput("sales", Decimal("142000000"), Decimal("1"), "Four strata sales."),
    ]
    with pytest.raises(ReconciliationError) as excinfo:
        reconcile(sales_only, basis="market", income_producing=True, purpose="loan")

    assert excinfo.value.code == "required_approach_missing"
    assert "income" in str(excinfo.value)
    assert "income stream" in str(excinfo.value)


def test_an_approach_at_zero_weight_does_not_satisfy_a_requirement():
    """Showing a number and declining to rely on it is not valuing on that basis."""
    shown_but_ignored = [
        ApproachInput("sales", Decimal("142000000"), Decimal("1"), "Four strata sales."),
        ApproachInput("income", Decimal("150000000"), Decimal("0"), "Computed but not relied upon."),
    ]
    with pytest.raises(ReconciliationError) as excinfo:
        reconcile(shown_but_ignored, income_producing=True, purpose="loan")
    assert excinfo.value.code == "required_approach_missing"


def test_insurable_value_excludes_market_and_income_evidence():
    """Reinstatement cost is not what the asset is worth."""
    policy = policy_for("insurable", income_producing=True)
    assert policy.required == ("cost",)
    assert set(policy.forbidden) == {"sales", "income"}

    wrong = [
        ApproachInput("cost", Decimal("120000000"), Decimal("0.5"), "Reinstatement."),
        ApproachInput("income", Decimal("150000000"), Decimal("0.5"), "Capitalised."),
    ]
    with pytest.raises(ReconciliationError) as excinfo:
        reconcile(wrong, basis="insurable", income_producing=True)
    assert excinfo.value.code == "forbidden_approach_used"


def test_a_forced_sale_basis_excludes_the_income_approach():
    """The assumed sale does not preserve the income stream it capitalises."""
    with pytest.raises(ReconciliationError) as excinfo:
        reconcile(
            [
                ApproachInput("sales", Decimal("100000000"), Decimal("0.5"), "a"),
                ApproachInput("income", Decimal("110000000"), Decimal("0.5"), "b"),
            ],
            basis="liquidation",
            income_producing=True,
        )
    assert excinfo.value.code == "forbidden_approach_used"


def test_approaches_that_disagree_wildly_are_refused_rather_than_averaged():
    """
    Two methods differing by half say one of them is wrong. Splitting the
    difference presents a midpoint neither supports.
    """
    with pytest.raises(ReconciliationError) as excinfo:
        reconcile(
            [
                ApproachInput("sales", Decimal("100000000"), Decimal("0.5"), "a"),
                ApproachInput("cost", Decimal("200000000"), Decimal("0.5"), "b"),
            ],
            basis="market",
        )
    assert excinfo.value.code == "approaches_diverge"
    assert "one of them is wrong" in str(excinfo.value)


def test_the_same_method_twice_is_refused():
    with pytest.raises(ReconciliationError, match="appears twice"):
        reconcile(
            [
                ApproachInput("sales", Decimal("100"), Decimal("0.5"), "a"),
                ApproachInput("sales", Decimal("110"), Decimal("0.5"), "b"),
            ]
        )


def test_the_concluded_value_is_the_weighted_sum_exactly():
    approaches = [
        ApproachInput("sales", Decimal("100000000"), Decimal("0.25"), "a"),
        ApproachInput("income", Decimal("120000000"), Decimal("0.60"), "b"),
        ApproachInput("cost", Decimal("110000000"), Decimal("0.15"), "c"),
    ]
    result = reconcile(approaches, income_producing=True, purpose="loan")
    expected = (
        Decimal("100000000") * Decimal("0.25")
        + Decimal("120000000") * Decimal("0.60")
        + Decimal("110000000") * Decimal("0.15")
    )
    assert result.concluded_value == expected.quantize(Decimal("0.01"))
