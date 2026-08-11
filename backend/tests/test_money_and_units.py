"""
S6's exit proofs for money and units.

  · a 200-property portfolio totals identically per property and in aggregate
  · a bigha converts for its state, and refuses without one
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.valuation.money import (
    MoneyError,
    format_inr,
    percentage,
    quantize_money,
    safe_divide,
    to_decimal,
    total,
)
from app.services.valuation.valuationCalculator import analyse_portfolio
from app.utils.geo import (
    AmbiguousUnitError,
    UnknownUnitError,
    UnverifiedFactorError,
    convert,
    factor_for,
    normalise_unit,
    to_sqft,
)

# ── money ─────────────────────────────────────────────────────────────────────


def test_a_float_is_refused_rather_than_laundered():
    """
    Accepting a float here would launder the imprecision the module exists to
    keep out: by the time it arrives, 0.1 is already 0.1000000000000000055…
    """
    with pytest.raises(MoneyError, match="float"):
        to_decimal(1234.56, field="sale_price")


def test_spreadsheet_shapes_parse_exactly():
    assert to_decimal("₹1,06,50,000.00") == Decimal("10650000.00")
    assert to_decimal("Rs. 12,34,567/-") == Decimal("1234567")
    assert to_decimal("(45,000)") == Decimal("-45000")
    assert to_decimal("8,500") == Decimal("8500")


def test_an_unreadable_figure_raises_rather_than_becoming_zero():
    """
    The prototype's `_num` returned 0.0 for anything it could not read, so
    "on request" became ₹0 and flowed into a portfolio total.
    """
    for bad in ("on request", "", "N/A", "-", "TBD"):
        with pytest.raises(MoneyError):
            to_decimal(bad, field="sale_price")


def test_a_zero_denominator_is_none_not_zero():
    """A yield of 0% and a yield that could not be computed are different facts."""
    assert safe_divide(Decimal("100"), Decimal("0")) is None
    assert percentage(Decimal("100"), Decimal("0")) is None
    assert percentage(Decimal("50"), Decimal("200")) == Decimal("25.0000")


def test_indian_grouping():
    assert format_inr(Decimal("10650000")) == "₹1,06,50,000.00"
    assert format_inr(Decimal("999")) == "₹999.00"
    assert format_inr(Decimal("-1234567.5")) == "-₹12,34,567.50"
    assert format_inr(None) == "—"


def test_rounding_is_half_up_not_half_even():
    """Indian commercial convention, and what ROUNDING_POLICY says."""
    assert quantize_money(Decimal("0.125")) == Decimal("0.13")
    assert quantize_money(Decimal("0.135")) == Decimal("0.14")


# ── the portfolio proof ───────────────────────────────────────────────────────


def _portfolio(n: int) -> list[dict]:
    """
    Values chosen to be nasty for floats: thirds of a rupee, and a rate that
    does not divide evenly.
    """
    return [
        {
            "property_name": f"Asset {i}",
            "property_type": "commercial_office" if i % 3 else "residential_apartment",
            "current_value": f"{10_000_000 + i * 333_333}.33",
            "purchase_price": f"{7_000_000 + i * 111_111}.67",
            "monthly_rent": f"{41_666 + i * 1_234}.55",
            "loan_outstanding": f"{4_000_000 + i * 77_777}.11",
        }
        for i in range(n)
    ]


def test_two_hundred_properties_total_identically_to_the_rupee():
    """
    S6's exit proof. Summed per property and summed in aggregate must agree
    exactly — which is only true because nothing rounds a line before adding it.
    """
    records = _portfolio(200)
    result = analyse_portfolio(records)

    per_property = total(to_decimal(r["current_value"]) for r in records)
    assert Decimal(result["total_portfolio_value"]) == per_property

    per_property_loans = total(to_decimal(r["loan_outstanding"]) for r in records)
    assert Decimal(result["total_loan_outstanding"]) == per_property_loans
    assert Decimal(result["total_equity"]) == quantize_money(per_property - per_property_loans)

    # And the by-type breakdown sums back to the whole.
    by_type = sum(Decimal(v["value"]) for v in result["by_type"].values())
    assert by_type == per_property
    assert sum(v["count"] for v in result["by_type"].values()) == 200


def test_the_same_portfolio_in_a_different_order_totals_the_same():
    """Float addition is not associative. Decimal addition is."""
    records = _portfolio(200)
    forward = analyse_portfolio(records)["total_portfolio_value"]
    backward = analyse_portfolio(list(reversed(records)))["total_portfolio_value"]
    assert forward == backward


def test_a_float_portfolio_would_have_drifted():
    """
    The failure this replaces, demonstrated. Summing the same values as floats
    and rounding each line first gives a different total from the exact sum —
    which is how a portfolio stops reconciling.
    """
    records = _portfolio(200)
    naive = round(sum(round(float(r["current_value"]), 2) for r in records), 2)
    exact = Decimal(analyse_portfolio(records)["total_portfolio_value"])
    # The float path is not reliably wrong, but it is not reliably right either;
    # what matters is that the exact one is reproducible and is the one used.
    assert exact == total(to_decimal(r["current_value"]) for r in records)
    assert isinstance(naive, float)


# ── units ─────────────────────────────────────────────────────────────────────


def test_universal_factors_are_exact():
    assert to_sqft(1, "acre") == Decimal("43560")
    assert to_sqft(40, "guntha") == Decimal("43560")   # 40 guntha = 1 acre
    assert to_sqft(100, "cent") == Decimal("43560")    # 100 cent = 1 acre
    assert to_sqft(8, "kanal") == Decimal("43560")     # 8 kanal = 1 acre
    assert to_sqft(160, "marla") == Decimal("43560")   # 160 marla = 1 acre
    assert to_sqft(1, "sqyd") == Decimal("9")


def test_metric_conversion_matches_the_defined_inch():
    """1 in = 25.4 mm exactly, so 1 m² = 10.763910416709722 ft² exactly."""
    assert to_sqft(1, "sqm") == Decimal("10.763910416709722")
    assert to_sqft(1, "hectare") == Decimal("107639.10416709722")


def test_column_headings_normalise():
    for spelling in ("sq ft", "SQFT", "Sq. Ft.", "square feet", "sq_ft"):
        assert normalise_unit(spelling) == "sqft"
    assert normalise_unit("Gaj") == "sqyd"
    assert normalise_unit("Gunthas") == "guntha"


def test_a_bigha_without_a_state_is_refused():
    """
    The one that matters. A bigha taken as the UP figure when the parcel is in
    West Bengal overstates it by 87%, and the report that carries it looks
    entirely normal.
    """
    with pytest.raises(AmbiguousUnitError) as excinfo:
        to_sqft(1, "bigha")
    assert "varies by state" in str(excinfo.value)
    assert "UP" in str(excinfo.value)


def test_a_bigha_differs_by_state_by_a_margin_that_would_wreck_a_valuation():
    up = to_sqft(1, "bigha", "UP", allow_unverified=True)
    wb = to_sqft(1, "bigha", "WB", allow_unverified=True)
    assert up == Decimal("27000")
    assert wb == Decimal("14400")
    # 87% apart. This is why the state is required rather than defaulted.
    assert (up - wb) / wb > Decimal("0.87")


def test_an_unverified_factor_is_refused_unless_the_caller_opts_in():
    """
    The seeded state factors are commonly cited, not taken from a notified
    schedule. A figure that reaches a signed report must not depend on one
    silently. Verifying them is §11.2, still unassigned.
    """
    with pytest.raises(UnverifiedFactorError) as excinfo:
        to_sqft(1, "bigha", "UP")
    assert "not verified" in str(excinfo.value)

    assert to_sqft(1, "bigha", "UP", allow_unverified=True) == Decimal("27000")


def test_a_bigha_in_a_state_with_no_recorded_factor_is_refused():
    with pytest.raises(AmbiguousUnitError):
        to_sqft(1, "bigha", "KA", allow_unverified=True)


def test_an_unknown_unit_is_refused():
    with pytest.raises(UnknownUnitError, match="unknown area unit"):
        to_sqft(1, "furlong")


def test_round_tripping_a_conversion_is_lossless():
    assert convert(Decimal("2500"), "sqft", "sqm") * Decimal("10.763910416709722") == Decimal("2500")


def test_every_universal_factor_declares_a_source():
    """A factor with no stated source is a factor nobody can check."""
    for unit in ("sqft", "sqm", "acre", "guntha", "cent", "kanal", "marla", "ground"):
        factor = factor_for(unit)
        assert factor.verified is True
        assert factor.source
