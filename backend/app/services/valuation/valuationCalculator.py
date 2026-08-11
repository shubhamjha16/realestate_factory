"""
Valuation Calculator — deterministic, `Decimal`, zero LLM calls.

Rewritten in S6. Every figure that was a float is now an exact `Decimal`, summed
exactly and rounded once at the end. That is what makes a portfolio total
identically whether it is summed per property or in aggregate — the property the
prototype did not have, and could not have, because `round(x, 2)` on binary
floats loses a different amount in each order of operations.

The comparable path changed more than its type. `analyse_comparables` no longer
returns a `suggested_rate`: a trimmed mean of unadjusted rates is not a value
conclusion, and pretending otherwise is the defect S7 closes. It now returns
pre-adjustment statistics under a name that says so, and the conclusion comes
from `salesComparison.conclude` over an adjustment grid.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.services.valuation.money import (
    ZERO,
    percentage,
    quantize_money,
    quantize_percent,
    quantize_rate,
    safe_divide,
    to_decimal,
    total,
)
from app.services.valuation.salesComparison import pre_adjustment_stats

VACANT = {"vacant", "empty", ""}
COMPLETE = {"completed", "done", "approved", "certified"}
PENDING = {"pending", "in progress", "ongoing", ""}


def _d(record: dict, key: str, default: str = "0") -> Decimal:
    value = record.get(key)
    if value is None or value == "":
        return Decimal(default)
    return to_decimal(value, field=key)


# ── Comparable sales ──────────────────────────────────────────────────────────


def analyse_comparables(records: list[dict]) -> dict:
    """
    Pre-adjustment statistics. **Not a value conclusion.**

    The prototype returned `suggested_rate` from this and the report printed it
    as the valuation. What it actually is: a sanity check on the raw evidence,
    useful for spotting a wild set before anyone spends an hour adjusting it.

    The conclusion comes from `salesComparison.conclude` over an adjustment grid
    built in `valuation/adjust.py`. There is deliberately no key here that a
    caller could mistake for one.
    """
    if not records:
        return {}

    rates: list[Decimal] = []
    for record in records:
        rate = _d(record, "rate_per_sqft") or _d(record, "price_per_sqft")
        if rate > 0:
            rates.append(rate)
            continue
        price, area = _d(record, "sale_price"), _d(record, "area")
        if price > 0 and area > 0:
            rates.append(price / area)

    stats = pre_adjustment_stats(rates)
    if stats is None:
        return {"comparable_count": len(records), "rates_derived": 0}

    return {
        "comparable_count": len(records),
        "rates_derived": stats.count,
        **stats.to_dict(),
        "requires_adjustment_grid": True,
        "note": (
            "These are unadjusted statistics. A value conclusion requires the "
            "adjustment grid — see services/valuation/adjust.py."
        ),
    }


def compute_market_value(area_sqft: Decimal | str, rate_per_sqft: Decimal | str) -> Decimal:
    return quantize_money(to_decimal(area_sqft, field="area_sqft") * to_decimal(rate_per_sqft, field="rate"))


# ── Income approach ───────────────────────────────────────────────────────────


def compute_rental_yield(annual_rent: Decimal | str, market_value: Decimal | str) -> Decimal | None:
    return percentage(to_decimal(annual_rent, field="annual_rent"), to_decimal(market_value, field="market_value"))


def compute_cap_rate(noi: Decimal | str, market_value: Decimal | str) -> Decimal | None:
    return percentage(to_decimal(noi, field="noi"), to_decimal(market_value, field="market_value"))


def compute_gdv(
    area_sqft: Decimal | str, rate_per_sqft: Decimal | str, sellable_pct: Decimal | str = "0.85"
) -> Decimal:
    """Gross Development Value — saleable area × rate."""
    return quantize_money(
        to_decimal(area_sqft, field="area_sqft")
        * to_decimal(sellable_pct, field="sellable_pct")
        * to_decimal(rate_per_sqft, field="rate")
    )


def compute_noi(
    gross_rent: Decimal | str,
    vacancy_rate_pct: Decimal | str = "5",
    opex_pct: Decimal | str = "20",
) -> Decimal:
    """
    Net Operating Income after vacancy and operating expenses.

    Both deductions apply to the figure the previous one left, and neither is
    rounded on the way through — rounding the effective rent before deducting
    opex changes the NOI, and the NOI drives the cap rate.
    """
    rent = to_decimal(gross_rent, field="gross_rent")
    vacancy = to_decimal(vacancy_rate_pct, field="vacancy_rate_pct")
    opex = to_decimal(opex_pct, field="opex_pct")

    effective = rent * (Decimal(1) - vacancy / Decimal(100))
    return quantize_money(effective * (Decimal(1) - opex / Decimal(100)))


# ── Rent roll ─────────────────────────────────────────────────────────────────


def analyse_rent_roll(records: list[dict]) -> dict:
    """
    The total must tie to the sum of the lines, to the rupee.

    Every line is summed exactly and the total rounded once. Rounding each line
    first is what makes a rent roll that does not tie — and a rent roll that does
    not tie is the first thing a lender's analyst notices.
    """
    if not records:
        return {}

    occupied = [r for r in records if str(r.get("status", "")).lower() not in VACANT]
    vacant = [r for r in records if str(r.get("status", "")).lower() in VACANT]

    monthly = total(_d(r, "monthly_rent") for r in occupied)
    line_areas = [_d(r, "area") for r in records]

    escalations = []
    for r in occupied:
        pct = _d(r, "escalation_pct")
        if pct <= 0:
            continue
        current = _d(r, "monthly_rent")
        escalations.append(
            {
                "unit": r.get("unit", ""),
                "tenant": r.get("tenant", ""),
                "current_rent": str(quantize_money(current)),
                "new_rent": str(quantize_money(current * (Decimal(1) + pct / Decimal(100)))),
                "escalation_pct": str(quantize_percent(pct)),
            }
        )

    return {
        "type": "rent_roll",
        "total_units": len(records),
        "occupied_units": len(occupied),
        "vacant_units": len(vacant),
        "vacancy_rate_pct": str(percentage(Decimal(len(vacant)), Decimal(len(records))) or ZERO),
        "total_area_sqft": str(total(line_areas)),
        "occupied_area_sqft": str(total(_d(r, "area") for r in occupied)),
        "total_monthly_rent": str(monthly),
        # Exactly twelve times the monthly total, computed from the unrounded
        # sum so the annual figure ties to the monthly one.
        "total_annual_rent": str(quantize_money(sum((_d(r, "monthly_rent") for r in occupied), ZERO) * 12)),
        "total_security_deposit": str(total(_d(r, "security_deposit") for r in records)),
        "total_overdue": str(total(_d(r, "overdue") for r in records)),
        "upcoming_escalations": escalations,
        "unit_details": records,
    }


# ── Construction disbursement ─────────────────────────────────────────────────


def analyse_construction_stages(records: list[dict], total_loan: Decimal | str = "0") -> dict:
    if not records:
        return {}

    loan = to_decimal(total_loan, field="total_loan")
    completed = [r for r in records if str(r.get("status", "")).lower() in COMPLETE]
    pending = [r for r in records if str(r.get("status", "")).lower() in PENDING]

    disbursed = total(_d(r, "disbursement_amount") for r in completed)
    overall = safe_divide(
        sum((_d(r, "completion_pct") for r in records), ZERO), Decimal(len(records))
    )

    return {
        "type": "construction",
        "total_stages": len(records),
        "completed_stages": len(completed),
        "pending_stages": len(pending),
        "overall_completion_pct": str(quantize_percent(overall) if overall is not None else ZERO),
        "total_disbursed": str(disbursed),
        "pending_disbursement": str(total(_d(r, "disbursement_amount") for r in pending)),
        "total_loan_amount": str(quantize_money(loan)),
        "utilisation_pct": str(percentage(disbursed, loan) or ZERO),
        "next_tranche": pending[0] if pending else None,
        "stage_details": records,
    }


# ── Portfolio ─────────────────────────────────────────────────────────────────


def analyse_portfolio(records: list[dict]) -> dict:
    """
    The exit proof: 200 properties total identically per property and in
    aggregate.

    Every component is summed exactly across all lines and rounded once. Nothing
    here rounds a line before adding it, which is the only way the two orders of
    summation can agree.
    """
    if not records:
        return {}

    values = [_d(r, "current_value") for r in records]
    costs = [_d(r, "purchase_price") for r in records]
    rents = [_d(r, "monthly_rent") for r in records]
    loans = [_d(r, "loan_outstanding") for r in records]

    exact_value = sum(values, ZERO)
    exact_cost = sum(costs, ZERO)
    exact_annual_rent = sum(rents, ZERO) * 12
    exact_loan = sum(loans, ZERO)

    by_type: dict[str, dict[str, Any]] = {}
    for record, value in zip(records, values, strict=True):
        key = str(record.get("property_type") or "Other")
        bucket = by_type.setdefault(key, {"count": 0, "value": ZERO})
        bucket["count"] += 1
        bucket["value"] += value

    return {
        "type": "portfolio",
        "total_properties": len(records),
        "total_portfolio_value": str(quantize_money(exact_value)),
        "total_cost": str(quantize_money(exact_cost)),
        "total_equity": str(quantize_money(exact_value - exact_loan)),
        "total_loan_outstanding": str(quantize_money(exact_loan)),
        "annual_rental_income": str(quantize_money(exact_annual_rent)),
        "portfolio_yield_pct": str(percentage(exact_annual_rent, exact_value) or ZERO),
        "appreciation_pct": str(percentage(exact_value - exact_cost, exact_cost) or ZERO),
        "by_type": {
            k: {"count": v["count"], "value": str(quantize_money(v["value"]))}
            for k, v in sorted(by_type.items())
        },
        "properties": records,
    }


# ── Entry point ───────────────────────────────────────────────────────────────


def compute(parsed_data: dict, job_type: str = "") -> dict:
    """
    Dispatch on the parsed format.

    An unknown format raises. The prototype fell through to
    `{"type": "raw", ...}` and let a report render over data nothing had
    understood.
    """
    fmt = parsed_data.get("format", "")
    records = parsed_data.get("records", [])

    if fmt == "comparables":
        return {"type": "comparables", **analyse_comparables(records)}
    if fmt == "lease_schedule":
        return analyse_rent_roll(records)
    if fmt == "construction_stages":
        return analyse_construction_stages(records)
    if fmt == "portfolio":
        return analyse_portfolio(records)
    if fmt == "land_records":
        return {
            "type": "land_records",
            "parcel_count": len(records),
            "total_area_sqft": str(total(_d(r, "area_sqft") for r in records)),
            "parcels": records,
        }

    raise ValueError(
        f"no computation is defined for parsed format {fmt!r}. "
        f"A report must not render over data nothing has understood."
    )
