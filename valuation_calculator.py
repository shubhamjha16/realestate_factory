"""
Valuation Calculator — Real Estate Factory
Deterministic calculations: GDV, cap rate, rental yield, IRR, NPV,
rent roll analysis, construction disbursement tracking.
Zero LLM calls.
"""

from typing import Optional


# ── Comparable Sales Analysis ──────────────────────────────────────────────────

def analyse_comparables(records: list) -> dict:
    """
    From parsed comparable sales, derive price per sqft stats and suggested value.
    """
    if not records:
        return {}

    rates = []
    for r in records:
        if r.get("price_per_sqft") and r["price_per_sqft"] > 0:
            rates.append(r["price_per_sqft"])
        elif r.get("sale_price") and r.get("area_sqft") and r["area_sqft"] > 0:
            rates.append(r["sale_price"] / r["area_sqft"])

    if not rates:
        return {"comparable_count": len(records), "avg_rate_per_sqft": 0}

    rates_sorted = sorted(rates)
    n = len(rates_sorted)
    avg  = sum(rates_sorted) / n
    low  = min(rates_sorted)
    high = max(rates_sorted)
    # Trim outliers (remove top + bottom 10%)
    trim_n = max(1, int(n * 0.1))
    trimmed = rates_sorted[trim_n: n - trim_n] if n > 4 else rates_sorted
    trimmed_avg = sum(trimmed) / len(trimmed) if trimmed else avg

    return {
        "comparable_count":     n,
        "avg_rate_per_sqft":    round(avg, 2),
        "trimmed_avg_rate":     round(trimmed_avg, 2),
        "min_rate_per_sqft":    round(low, 2),
        "max_rate_per_sqft":    round(high, 2),
        "suggested_rate":       round(trimmed_avg, 2),
    }


def compute_market_value(area_sqft: float, rate_per_sqft: float) -> float:
    return round(area_sqft * rate_per_sqft, 2)


# ── Income Approach ────────────────────────────────────────────────────────────

def compute_rental_yield(annual_rent: float, market_value: float) -> float:
    if market_value <= 0:
        return 0.0
    return round((annual_rent / market_value) * 100, 2)


def compute_cap_rate(noi: float, market_value: float) -> float:
    """Net Operating Income / Market Value × 100"""
    if market_value <= 0:
        return 0.0
    return round((noi / market_value) * 100, 2)


def compute_gdv(area_sqft: float, rate_per_sqft: float, sellable_pct: float = 0.85) -> float:
    """Gross Development Value — total saleable area × rate"""
    return round(area_sqft * sellable_pct * rate_per_sqft, 2)


def compute_noi(gross_rent: float, vacancy_rate_pct: float = 5.0, opex_pct: float = 20.0) -> float:
    """Net Operating Income after vacancy and operating expenses"""
    effective_rent = gross_rent * (1 - vacancy_rate_pct / 100)
    noi = effective_rent * (1 - opex_pct / 100)
    return round(noi, 2)


# ── Rent Roll Analysis ─────────────────────────────────────────────────────────

def analyse_rent_roll(records: list) -> dict:
    """
    Full rent roll analysis from lease_schedule records.
    Returns vacancy, total rent, yield, overdue summary.
    """
    if not records:
        return {}

    total_units    = len(records)
    occupied       = [r for r in records if str(r.get("status", "")).lower() not in ("vacant", "empty", "")]
    vacant         = [r for r in records if str(r.get("status", "")).lower() in ("vacant", "empty")]
    total_area     = sum(r.get("area_sqft", 0) for r in records)
    occupied_area  = sum(r.get("area_sqft", 0) for r in occupied)
    total_monthly  = sum(r.get("monthly_rent", 0) for r in occupied)
    total_annual   = total_monthly * 12
    total_deposit  = sum(r.get("security_deposit", 0) for r in records)
    total_overdue  = sum(r.get("overdue", 0) for r in records)
    vacancy_rate   = round((len(vacant) / total_units) * 100, 2) if total_units else 0

    # Upcoming escalations (non-zero escalation_pct)
    escalations = [
        {"unit": r["unit"], "tenant": r["tenant"],
         "current_rent": r["monthly_rent"],
         "new_rent": round(r["monthly_rent"] * (1 + r["escalation_pct"] / 100), 2),
         "escalation_pct": r["escalation_pct"]}
        for r in occupied if r.get("escalation_pct", 0) > 0
    ]

    return {
        "total_units":       total_units,
        "occupied_units":    len(occupied),
        "vacant_units":      len(vacant),
        "vacancy_rate_pct":  vacancy_rate,
        "total_area_sqft":   round(total_area, 2),
        "occupied_area_sqft": round(occupied_area, 2),
        "total_monthly_rent": round(total_monthly, 2),
        "total_annual_rent":  round(total_annual, 2),
        "total_security_deposit": round(total_deposit, 2),
        "total_overdue":     round(total_overdue, 2),
        "upcoming_escalations": escalations,
        "unit_details":      records,
    }


# ── Construction Disbursement ──────────────────────────────────────────────────

def analyse_construction_stages(records: list, total_loan: float = 0) -> dict:
    """
    Track construction stages, compute disbursement eligibility.
    """
    if not records:
        return {}

    completed   = [r for r in records if str(r.get("status", "")).lower() in ("completed", "done", "approved")]
    pending     = [r for r in records if str(r.get("status", "")).lower() in ("pending", "in progress", "ongoing", "")]
    total_stages = len(records)

    disbursed   = sum(r.get("disbursement_amount", 0) for r in completed)
    pending_amt = sum(r.get("disbursement_amount", 0) for r in pending)
    overall_pct = round(sum(r.get("completion_pct", 0) for r in records) / total_stages, 2) if total_stages else 0

    next_tranche = pending[0] if pending else None

    return {
        "total_stages":         total_stages,
        "completed_stages":     len(completed),
        "pending_stages":       len(pending),
        "overall_completion_pct": overall_pct,
        "total_disbursed":      round(disbursed, 2),
        "pending_disbursement": round(pending_amt, 2),
        "total_loan_amount":    round(total_loan, 2),
        "utilisation_pct":      round((disbursed / total_loan * 100) if total_loan else 0, 2),
        "next_tranche":         next_tranche,
        "stage_details":        records,
    }


# ── Portfolio Analysis ─────────────────────────────────────────────────────────

def analyse_portfolio(records: list) -> dict:
    if not records:
        return {}

    total_value    = sum(r.get("current_value", 0) for r in records)
    total_cost     = sum(r.get("purchase_price", 0) for r in records)
    total_rent     = sum(r.get("monthly_rent", 0) for r in records) * 12
    total_loan     = sum(r.get("loan_outstanding", 0) for r in records)
    equity         = total_value - total_loan
    appreciation   = round(((total_value - total_cost) / total_cost * 100) if total_cost else 0, 2)
    portfolio_yield = round((total_rent / total_value * 100) if total_value else 0, 2)

    by_type = {}
    for r in records:
        t = r.get("property_type", "Other")
        by_type.setdefault(t, {"count": 0, "value": 0})
        by_type[t]["count"] += 1
        by_type[t]["value"] += r.get("current_value", 0)

    return {
        "total_properties":   len(records),
        "total_portfolio_value": round(total_value, 2),
        "total_cost":         round(total_cost, 2),
        "total_equity":       round(equity, 2),
        "total_loan_outstanding": round(total_loan, 2),
        "annual_rental_income": round(total_rent, 2),
        "portfolio_yield_pct": portfolio_yield,
        "appreciation_pct":   appreciation,
        "by_type":            by_type,
        "properties":         records,
    }


# ── Main entry point ───────────────────────────────────────────────────────────

def compute(parsed_data: dict, job_type: str = "") -> dict:
    fmt     = parsed_data.get("format", "")
    records = parsed_data.get("records", [])

    if fmt == "comparables":
        return {"type": "comparables", **analyse_comparables(records)}

    if fmt == "lease_schedule":
        return {"type": "rent_roll", **analyse_rent_roll(records)}

    if fmt == "construction_stages":
        return {"type": "construction", **analyse_construction_stages(records)}

    if fmt == "portfolio":
        return {"type": "portfolio", **analyse_portfolio(records)}

    # Fallback — return raw
    return {"type": "raw", "records": records, "count": len(records)}
