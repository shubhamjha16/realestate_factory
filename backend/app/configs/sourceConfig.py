"""
Input format registry and schema versions.

S1 records what the parser already recognises, with the version each shape is
pinned at. S6 turns this registry into the thing `ingest/detect.py` consults and
`ingest/schemas/` validates against, at which point an unrecognised format
becomes an error rather than an empty structure.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceFormat:
    key: str
    label: str
    version: str
    # Headers whose presence identifies the format today (see propertyDataParser).
    detect_headers: tuple[str, ...]
    required_fields: tuple[str, ...] = field(default_factory=tuple)


COMPARABLES = SourceFormat(
    key="comparables",
    label="Comparable sales",
    version="1.0",
    detect_headers=("sale_price", "sale price", "transaction_value", "market_value"),
    required_fields=("area_sqft", "sale_price"),
)

LEASE_SCHEDULE = SourceFormat(
    key="lease_schedule",
    label="Lease schedule / rent roll",
    version="1.0",
    detect_headers=("tenant", "tenant_name", "monthly_rent", "lease_start", "lease_end"),
    required_fields=("unit", "monthly_rent"),
)

CONSTRUCTION_STAGES = SourceFormat(
    key="construction_stages",
    label="Construction stages",
    version="1.0",
    detect_headers=("stage", "milestone", "completion_%", "disbursement_amount"),
    required_fields=("stage", "completion_pct"),
)

PORTFOLIO = SourceFormat(
    key="portfolio",
    label="Portfolio",
    version="1.0",
    detect_headers=("property_id", "property_name", "property_type", "current_value"),
    required_fields=("property_name", "current_value"),
)

LAND_RECORDS = SourceFormat(
    key="land_records",
    label="Land records",
    version="1.0",
    detect_headers=("survey_no", "sy_no", "khata", "owner_name", "area_sqft", "area_sqm"),
    required_fields=("survey_no",),
)

# Detection order matters and matches the parser's cascade exactly.
SOURCE_FORMATS: tuple[SourceFormat, ...] = (
    COMPARABLES,
    LEASE_SCHEDULE,
    CONSTRUCTION_STAGES,
    PORTFOLIO,
    LAND_RECORDS,
)

SOURCE_FORMATS_BY_KEY = {f.key: f for f in SOURCE_FORMATS}
