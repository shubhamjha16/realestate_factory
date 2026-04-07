"""
Property Data Parser — Real Estate Factory
Parses: comparable sales CSV, lease schedule CSV, rent roll CSV,
        land records CSV, construction stage CSV, portfolio CSV.
Auto-detects format. Returns structured dict for valuation_calculator.
"""

import csv, io, json


def parse_property_data(raw: str, hint: str = "") -> dict:
    raw = raw.strip()
    if not raw:
        return {"format": "empty", "records": [], "metadata": {}}

    # JSON input
    if raw.startswith("{") or raw.startswith("["):
        try:
            data = json.loads(raw)
            return {"format": "json", "records": data if isinstance(data, list) else [data], "metadata": {}}
        except Exception:
            pass

    # CSV — detect sub-type from headers
    try:
        reader = csv.DictReader(io.StringIO(raw))
        rows   = list(reader)
        if not rows:
            return {"format": "empty_csv", "records": [], "metadata": {}}

        headers = {k.lower().strip() for k in rows[0].keys()}

        # Comparable sales
        if any(h in headers for h in ("sale_price", "sale price", "transaction_value", "market_value")):
            return _parse_comparables(rows)

        # Lease schedule / rent roll
        if any(h in headers for h in ("tenant", "tenant_name", "monthly_rent", "lease_start", "lease_end")):
            return _parse_lease_schedule(rows)

        # Construction stages
        if any(h in headers for h in ("stage", "milestone", "completion_%", "disbursement_amount")):
            return _parse_construction_stages(rows)

        # Portfolio (multi-property)
        if any(h in headers for h in ("property_id", "property_name", "property_type", "current_value")):
            return _parse_portfolio(rows)

        # Land records / encumbrance
        if any(h in headers for h in ("survey_no", "sy_no", "khata", "owner_name", "area_sqft", "area_sqm")):
            return _parse_land_records(rows)

        # Generic fallback
        return {"format": "generic_csv", "records": [{k.lower(): v for k, v in r.items()} for r in rows], "metadata": {}}

    except Exception as e:
        return {"format": "parse_error", "records": [], "metadata": {"error": str(e)}}


# ── Comparable Sales ───────────────────────────────────────────────────────────

def _parse_comparables(rows: list) -> dict:
    records = []
    for r in rows:
        keys = {k.lower().strip(): v for k, v in r.items()}
        records.append({
            "address":          keys.get("address") or keys.get("property_address") or "",
            "area_sqft":        _num(keys.get("area_sqft") or keys.get("area") or "0"),
            "sale_price":       _num(keys.get("sale_price") or keys.get("transaction_value") or keys.get("market_value") or "0"),
            "price_per_sqft":   _num(keys.get("price_per_sqft") or keys.get("rate_per_sqft") or "0"),
            "sale_date":        keys.get("sale_date") or keys.get("date") or "",
            "property_type":    keys.get("property_type") or keys.get("type") or "",
            "floor":            keys.get("floor") or "",
            "locality":         keys.get("locality") or keys.get("area_name") or "",
        })
    return {"format": "comparables", "records": records, "metadata": {"count": len(records)}}


# ── Lease Schedule / Rent Roll ─────────────────────────────────────────────────

def _parse_lease_schedule(rows: list) -> dict:
    records = []
    for r in rows:
        keys = {k.lower().strip(): v for k, v in r.items()}
        records.append({
            "unit":             keys.get("unit") or keys.get("flat_no") or keys.get("shop_no") or "",
            "tenant":           keys.get("tenant") or keys.get("tenant_name") or "",
            "area_sqft":        _num(keys.get("area_sqft") or keys.get("area") or "0"),
            "monthly_rent":     _num(keys.get("monthly_rent") or keys.get("rent") or "0"),
            "security_deposit": _num(keys.get("security_deposit") or keys.get("deposit") or "0"),
            "lease_start":      keys.get("lease_start") or keys.get("start_date") or "",
            "lease_end":        keys.get("lease_end") or keys.get("end_date") or "",
            "escalation_pct":   _num(keys.get("escalation_%") or keys.get("escalation_pct") or keys.get("increment_pct") or "0"),
            "status":           keys.get("status") or keys.get("occupancy_status") or "occupied",
            "overdue":          _num(keys.get("overdue") or keys.get("arrears") or "0"),
        })
    return {"format": "lease_schedule", "records": records, "metadata": {"count": len(records)}}


# ── Construction Stages ────────────────────────────────────────────────────────

def _parse_construction_stages(rows: list) -> dict:
    records = []
    for r in rows:
        keys = {k.lower().strip(): v for k, v in r.items()}
        records.append({
            "stage":                keys.get("stage") or keys.get("milestone") or "",
            "description":          keys.get("description") or "",
            "completion_pct":       _num(keys.get("completion_%") or keys.get("completion_pct") or "0"),
            "disbursement_amount":  _num(keys.get("disbursement_amount") or keys.get("tranche_amount") or "0"),
            "disbursement_pct":     _num(keys.get("disbursement_%") or keys.get("disbursement_pct") or "0"),
            "status":               keys.get("status") or "",
            "target_date":          keys.get("target_date") or "",
            "actual_date":          keys.get("actual_date") or "",
            "remarks":              keys.get("remarks") or "",
        })
    return {"format": "construction_stages", "records": records, "metadata": {"count": len(records)}}


# ── Portfolio ──────────────────────────────────────────────────────────────────

def _parse_portfolio(rows: list) -> dict:
    records = []
    for r in rows:
        keys = {k.lower().strip(): v for k, v in r.items()}
        records.append({
            "property_id":    keys.get("property_id") or "",
            "property_name":  keys.get("property_name") or keys.get("name") or "",
            "property_type":  keys.get("property_type") or keys.get("type") or "",
            "locality":       keys.get("locality") or keys.get("location") or "",
            "area_sqft":      _num(keys.get("area_sqft") or keys.get("area") or "0"),
            "current_value":  _num(keys.get("current_value") or keys.get("market_value") or "0"),
            "purchase_price": _num(keys.get("purchase_price") or keys.get("cost") or "0"),
            "monthly_rent":   _num(keys.get("monthly_rent") or keys.get("rent") or "0"),
            "occupancy":      keys.get("occupancy") or keys.get("status") or "",
            "loan_outstanding": _num(keys.get("loan_outstanding") or keys.get("mortgage") or "0"),
        })
    return {"format": "portfolio", "records": records, "metadata": {"count": len(records)}}


# ── Land Records ───────────────────────────────────────────────────────────────

def _parse_land_records(rows: list) -> dict:
    records = []
    for r in rows:
        keys = {k.lower().strip(): v for k, v in r.items()}
        records.append({
            "survey_no":    keys.get("survey_no") or keys.get("sy_no") or "",
            "khata_no":     keys.get("khata") or keys.get("khata_no") or "",
            "owner_name":   keys.get("owner_name") or keys.get("owner") or "",
            "area_sqft":    _num(keys.get("area_sqft") or "0"),
            "area_sqm":     _num(keys.get("area_sqm") or "0"),
            "land_use":     keys.get("land_use") or keys.get("zoning") or "",
            "encumbrance":  keys.get("encumbrance") or keys.get("ec_status") or "",
            "remarks":      keys.get("remarks") or "",
        })
    return {"format": "land_records", "records": records, "metadata": {"count": len(records)}}


def _num(val) -> float:
    try:
        return float(str(val).replace(",", "").replace("₹", "").replace("Rs", "").strip())
    except (ValueError, TypeError):
        return 0.0
