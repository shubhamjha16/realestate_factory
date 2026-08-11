"""
S7's exit proofs — the adjustment grid.

The central one: **the same eight comparables produce a materially different,
and defensibly better, rate than the old trimmed mean.** That case is
`test_the_grid_produces_a_different_rate_than_the_trimmed_mean`, and the two
figures are printed side by side so the difference is visible in the commit
rather than asserted in the abstract.

The set is the golden valuation case: eight sales around Sector 62, Noida,
against a subject of 1,450 sq ft on the 6th floor, built 2016, freehold, valued
at 1 March 2026.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.services.valuation.adjust import (
    ADJUSTMENT_ORDER,
    Adjustment,
    AdjustmentError,
    AdjustmentGrid,
    apply_adjustments,
    build_grid,
)
from app.services.valuation.salesComparison import conclude, pre_adjustment_stats
from app.validators.comparableValidator import (
    AdequacyPolicy,
    ComparableEvidenceError,
    validate_grid,
)

VALUATION_DATE = date(2026, 3, 1)
SUBJECT_AREA = Decimal("1450")

# The golden case's eight comparables, with the adjustments a valuer would
# actually apply against a 6th-floor, 2016-built, 1,450 sq ft freehold subject.
EIGHT_COMPARABLES = [
    {
        "id": "c1", "address": "Tower A Unit 604 Sector 62",
        "sale_price": "10650000", "area_sqft": "1420", "sale_date": date(2025, 11, 14),
        "adjustments": [
            {"factor": "time", "pct": "2.5", "rationale":
             "Sold Nov 2025; the locality index has risen ~0.8% a quarter to the valuation date."},
        ],
    },
    {
        "id": "c2", "address": "Tower B Unit 1102 Sector 62",
        "sale_price": "11780000", "area_sqft": "1510", "sale_date": date(2025, 10, 2),
        "adjustments": [
            {"factor": "time", "pct": "3.3", "rationale":
             "Sold Oct 2025; five months of movement to the valuation date."},
            {"factor": "floor", "pct": "-4", "rationale":
             "11th floor against the subject's 6th; the local market pays a premium for higher floors."},
            {"factor": "size", "pct": "1", "rationale":
             "1,510 sq ft against 1,450; the larger unit carries a small quantum discount."},
        ],
    },
    {
        "id": "c3", "address": "Tower C Unit 302 Sector 61",
        "sale_price": "9970000", "area_sqft": "1385", "sale_date": date(2025, 9, 19),
        "adjustments": [
            {"factor": "time", "pct": "4.1", "rationale":
             "Sold Sep 2025; five and a half months of movement."},
            {"factor": "location", "pct": "3", "rationale":
             "Sector 61 is marginally inferior to Sector 62 on metro access and school catchment."},
            {"factor": "floor", "pct": "2", "rationale":
             "3rd floor against the subject's 6th."},
        ],
    },
    {
        "id": "c4", "address": "Tower A Unit 1401 Sector 62",
        "sale_price": "11890000", "area_sqft": "1450", "sale_date": date(2026, 1, 8),
        "adjustments": [
            {"factor": "time", "pct": "0.5", "rationale":
             "Sold Jan 2026; close to the valuation date."},
            {"factor": "floor", "pct": "-5", "rationale":
             "14th floor against the subject's 6th; the premium above the podium is well established here."},
        ],
    },
    {
        "id": "c5", "address": "Tower D Unit 205 Sector 62",
        "sale_price": "9520000", "area_sqft": "1360", "sale_date": date(2025, 8, 27),
        "adjustments": [
            {"factor": "time", "pct": "4.8", "rationale":
             "Sold Aug 2025; six months of movement to the valuation date."},
            {"factor": "floor", "pct": "3", "rationale":
             "2nd floor against the subject's 6th."},
            {"factor": "condition", "pct": "2", "rationale":
             "Sold in bare-shell condition; the subject is fitted out to a builder finish."},
        ],
    },
    {
        "id": "c6", "address": "Tower B Unit 806 Sector 63",
        "sale_price": "10910000", "area_sqft": "1495", "sale_date": date(2025, 12, 11),
        "adjustments": [
            {"factor": "time", "pct": "1.7", "rationale":
             "Sold Dec 2025; under three months of movement."},
            {"factor": "location", "pct": "4", "rationale":
             "Sector 63 is predominantly commercial; residential stock there trades below Sector 62."},
        ],
    },
    {
        "id": "c7", "address": "Tower E Unit 1802 Sector 62",
        "sale_price": "13770000", "area_sqft": "1620", "sale_date": date(2026, 2, 3),
        "adjustments": [
            {"factor": "time", "pct": "0.2", "rationale":
             "Sold Feb 2026; effectively at the valuation date."},
            {"factor": "floor", "pct": "-6", "rationale":
             "18th floor with an unobstructed aspect, against the subject's 6th."},
            {"factor": "size", "pct": "2", "rationale":
             "1,620 sq ft against 1,450; quantum discount on the larger unit."},
            {"factor": "view", "pct": "-3", "rationale":
             "Faces the central green; the subject overlooks the internal driveway."},
        ],
    },
    {
        "id": "c8", "address": "Tower C Unit 101 Sector 61",
        "sale_price": "8580000", "area_sqft": "1300", "sale_date": date(2025, 7, 15),
        "adjustments": [
            {"factor": "time", "pct": "5.5", "rationale":
             "Sold Jul 2025; seven and a half months of movement, the oldest in the set."},
            {"factor": "location", "pct": "3", "rationale":
             "Sector 61, as above."},
            {"factor": "floor", "pct": "4", "rationale":
             "Ground-adjacent 1st floor; the least favoured level in this development."},
            {"factor": "condition", "pct": "3", "rationale":
             "Original 2016 fit-out, unrenovated."},
        ],
    },
]


@pytest.fixture
def grid() -> AdjustmentGrid:
    return build_grid(EIGHT_COMPARABLES)


# ── the central proof ─────────────────────────────────────────────────────────


def test_the_grid_produces_a_different_rate_than_the_trimmed_mean(grid, capsys):
    """
    S7's exit proof, with both figures shown.

    The trimmed mean averages raw price-per-sqft across sales on floors 1 to 18,
    in two sectors, spread over eight months. The grid restates each of them as
    though it had transacted here, now, on the subject's floor — and then
    averages. The difference is the work.
    """
    raw_rates = [c.raw_rate for c in grid.comparables]
    stats = pre_adjustment_stats(raw_rates)
    assert stats is not None

    result = conclude(grid, subject_area_sqft=SUBJECT_AREA, valuation_date=VALUATION_DATE)

    old_rate = stats.trimmed_mean_rate
    new_rate = result.concluded_rate
    old_value = (old_rate * SUBJECT_AREA).quantize(Decimal("0.01"))

    with capsys.disabled():
        print("\n  ── S7: the same eight comparables ──────────────────────────")
        print(f"  before (trimmed mean of raw rates) : ₹{old_rate}/sqft  → ₹{old_value}")
        print(f"  after  ({result.basis})")
        print(f"                                      : ₹{new_rate}/sqft  → ₹{result.indicated_value}")
        print(f"  movement                            : {(new_rate - old_rate) / old_rate * 100:.2f}%")
        print(f"  adjusted spread                     : {grid.spread_pct()}%")
        print(f"  mean gross adjustment               : {grid.mean_gross_adjustment_pct()}%")
        print("  ────────────────────────────────────────────────────────────")

    # Materially different: not a rounding artefact.
    movement = abs(new_rate - old_rate) / old_rate * 100
    assert movement > Decimal("1"), f"only {movement}% apart — the grid is not doing work"

    # Defensibly better: adjustment narrows the disagreement between the sales.
    assert grid.spread_pct() < (stats.spread_pct or Decimal("999"))


def test_the_conclusion_no_longer_comes_from_a_key_called_suggested_rate():
    """
    The prototype's `analyse_comparables` returned `suggested_rate` and the
    report printed it as the valuation. There is deliberately no key a caller
    could mistake for a conclusion any more.
    """
    from app.services.valuation.valuationCalculator import analyse_comparables

    computed = analyse_comparables(
        [{"sale_price": "10650000", "area": "1420"}, {"sale_price": "11780000", "area": "1510"}]
    )
    assert "suggested_rate" not in computed
    assert computed["requires_adjustment_grid"] is True
    assert "trimmed_mean_rate_sanity_only" in computed


# ── the grid itself ───────────────────────────────────────────────────────────


def test_adjustments_compound_rather_than_add(grid):
    """+10% then +10% is +21%. Summing them understates every multi-factor row."""
    adjusted = apply_adjustments(
        comparable_id="x", address="X", sale_price="1000000", area_sqft="1000",
        adjustments=[
            Adjustment("time", Decimal("10"), "a"),
            Adjustment("floor", Decimal("10"), "b"),
        ],
    )
    assert adjusted.raw_rate == Decimal("1000.0000")
    assert adjusted.adjusted_rate == Decimal("1210.0000")
    assert adjusted.net_adjustment_pct == Decimal("21.0000")


def test_adjustments_are_applied_in_the_defined_order(grid):
    """
    The order is in the report. Applying them in another order produces a
    different number than the report explains.
    """
    for comparable in grid.comparables:
        applied = [a.factor for a in comparable.adjustments]
        assert applied == sorted(applied, key=ADJUSTMENT_ORDER.index)


def test_an_adjustment_without_a_rationale_is_refused():
    """The grid is the defensibility. A percentage nobody explained cannot be reviewed."""
    with pytest.raises(AdjustmentError, match="no rationale"):
        Adjustment("floor", Decimal("5"), "   ")


def test_an_unknown_factor_is_refused():
    with pytest.raises(AdjustmentError, match="unknown adjustment factor"):
        Adjustment("vibes", Decimal("5"), "it felt right")


def test_an_adjustment_beyond_fifty_percent_is_refused():
    """Past that, the property is not a comparable — reject it instead."""
    with pytest.raises(AdjustmentError, match="not a comparable"):
        Adjustment("location", Decimal("60"), "a different city entirely")


def test_two_adjustments_on_the_same_factor_are_refused():
    with pytest.raises(AdjustmentError, match="two floor adjustments"):
        apply_adjustments(
            comparable_id="x", address="X", sale_price="1000000", area_sqft="1000",
            adjustments=[
                Adjustment("floor", Decimal("5"), "a"),
                Adjustment("floor", Decimal("-3"), "b"),
            ],
        )


def test_gross_adjustment_is_reported_alongside_net(grid):
    """
    +15% and −15% nets to zero but has moved the comparable 30%. A set with large
    gross adjustments was not very comparable to begin with, and that is a
    conclusion about the evidence.
    """
    c7 = next(c for c in grid.comparables if c.comparable_id == "c7")
    assert c7.gross_adjustment_pct == Decimal("11.2000")   # 0.2 + 6 + 2 + 3
    assert abs(c7.net_adjustment_pct) < c7.gross_adjustment_pct


def test_the_grid_renders_a_line_a_reviewer_can_follow(grid):
    c3 = next(c for c in grid.comparables if c.comparable_id == "c3")
    lines = c3.rationale_lines
    assert any(line.startswith("Location: +3%") for line in lines)
    assert all("—" in line and len(line) > 30 for line in lines)


def test_every_comparable_carries_its_raw_and_adjusted_rate(grid):
    """Both, always. A grid that shows only the result hides the work."""
    payload = grid.to_dict()
    for row in payload["comparables"]:
        assert Decimal(row["raw_rate"]) > 0
        assert Decimal(row["adjusted_rate"]) > 0
        assert row["adjustments"]


# ── the validator ─────────────────────────────────────────────────────────────


def test_a_valuation_with_two_comparables_is_refused_naming_the_minimum():
    small = build_grid(EIGHT_COMPARABLES[:2])
    with pytest.raises(ComparableEvidenceError) as excinfo:
        validate_grid(small, valuation_date=VALUATION_DATE)

    assert excinfo.value.code == "insufficient_comparables"
    assert "below the minimum of 3" in str(excinfo.value)
    assert excinfo.value.detail == {"count": 2, "minimum": 3}


def test_the_eight_comparable_set_passes_every_check(grid):
    validate_grid(grid, valuation_date=VALUATION_DATE)


def test_a_wide_adjusted_spread_is_blocked_with_the_outliers_named():
    """
    The blocking check S7 exists for. If the adjusted rates still disagree, the
    adjustments did not explain the differences — so their mean has nothing
    underneath it.
    """
    wild = [
        *EIGHT_COMPARABLES[:3],
        {
            "id": "outlier", "address": "Distress sale, Tower Z",
            "sale_price": "5200000", "area_sqft": "1400", "sale_date": date(2025, 12, 1),
            "adjustments": [
                {"factor": "distress", "pct": "10", "rationale":
                 "Sold under a lender's enforcement; a partial allowance only."},
            ],
        },
    ]
    grid = build_grid(wild)

    with pytest.raises(ComparableEvidenceError) as excinfo:
        validate_grid(grid, valuation_date=VALUATION_DATE)

    assert excinfo.value.code == "adjusted_spread_too_wide"
    assert "Distress sale, Tower Z" in str(excinfo.value)
    assert "did not explain the differences" in str(excinfo.value)


def test_stale_comparables_are_blocked_and_named():
    old = [
        {**c, "sale_date": date(2021, 1, 1)} for c in EIGHT_COMPARABLES[:4]
    ]
    grid = build_grid(old)
    with pytest.raises(ComparableEvidenceError) as excinfo:
        validate_grid(grid, valuation_date=VALUATION_DATE)

    assert excinfo.value.code == "stale_comparables"
    assert "dominant assumption" in str(excinfo.value)


def test_distant_comparables_are_blocked_and_named(grid):
    distances = {c.address: Decimal("50000") for c in grid.comparables[:2]}
    distances.update({c.address: Decimal("500") for c in grid.comparables[2:]})

    with pytest.raises(ComparableEvidenceError) as excinfo:
        validate_grid(grid, valuation_date=VALUATION_DATE, distances_m=distances)

    assert excinfo.value.code == "distant_comparables"
    assert "different market" in str(excinfo.value)


def test_the_policy_comes_from_settings():
    policy = AdequacyPolicy.from_settings()
    assert policy.min_sample == 3
    assert policy.max_age_months == 18
    assert policy.max_radius_m == 2000


# ── the conclusion ────────────────────────────────────────────────────────────


def test_the_value_range_comes_from_the_evidence_not_a_bracket(grid):
    """
    ±10% around a conclusion tells a reader nothing. The span of the adjusted
    rates tells them what the evidence actually supports.
    """
    result = conclude(grid, subject_area_sqft=SUBJECT_AREA)
    rates = grid.adjusted_rates

    assert result.value_range_low == (min(rates) * SUBJECT_AREA).quantize(Decimal("0.01"))
    assert result.value_range_high == (max(rates) * SUBJECT_AREA).quantize(Decimal("0.01"))
    assert result.value_range_low < result.indicated_value < result.value_range_high


def test_a_small_sample_concludes_on_the_median_and_says_so():
    small = build_grid(EIGHT_COMPARABLES[:4])
    result = conclude(small, subject_area_sqft=SUBJECT_AREA)
    assert "median" in result.basis
    assert result.concluded_rate == small.median_adjusted_rate()


def test_a_full_sample_concludes_on_the_mean(grid):
    result = conclude(grid, subject_area_sqft=SUBJECT_AREA)
    assert "mean of 8" in result.basis
    assert result.concluded_rate == grid.mean_adjusted_rate()


def test_an_empty_grid_cannot_conclude():
    with pytest.raises(ValueError, match="empty grid"):
        conclude(AdjustmentGrid(), subject_area_sqft=SUBJECT_AREA)


def test_the_result_carries_the_whole_grid_for_the_report(grid):
    payload = conclude(grid, subject_area_sqft=SUBJECT_AREA).to_dict()
    assert payload["method"] == "sales"
    assert len(payload["adjustment_grid"]["comparables"]) == 8
    # The pre-adjustment statistics travel too, so the report can show the work.
    assert payload["pre_adjustment"]["trimmed_mean_rate_sanity_only"]
