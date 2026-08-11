"""
The five input formats, as data.

Each carries a schema version. A format whose shape changes gets a new version
rather than a silently different meaning, so a re-parse of an old import is
either identical or an explicit migration.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.ingest.schemas.fields import (
    Field,
    as_date,
    as_int,
    as_non_negative_decimal,
    as_optional_date,
    as_optional_text,
    as_positive_decimal,
    as_text,
    one_of,
)


@dataclass(frozen=True)
class SourceSchema:
    key: str
    label: str
    version: str
    fields: tuple[Field, ...]
    # Columns whose presence identifies this format. Detection is a signal, never
    # the last word — the caller can always name the format explicitly.
    signature: tuple[str, ...]
    # Fields whose combination identifies one row. A second row with the same
    # values is a duplicate, not a second comparable.
    identity: tuple[str, ...]

    @property
    def required_fields(self) -> tuple[Field, ...]:
        return tuple(f for f in self.fields if f.required)


COMPARABLES = SourceSchema(
    key="comparables",
    label="Comparable sales",
    version="2.0",
    signature=("sale_price", "transaction_value", "rate_per_sqft", "price_per_sqft"),
    identity=("address", "sale_date", "sale_price"),
    fields=(
        Field("address", ("address", "property_address", "location"), required=True, coerce=as_text),
        Field("locality", ("locality", "area_name", "sector"), coerce=as_optional_text),
        # Required: a comparable with no area cannot produce a rate, and a rate is
        # the only thing a comparable is for.
        Field("area", ("area_sqft", "area", "built_up_area", "saleable_area"),
              required=True, coerce=as_positive_decimal),
        Field("area_unit", ("area_unit", "unit"), coerce=as_optional_text, default="sqft"),
        Field("sale_price", ("sale_price", "transaction_value", "market_value", "consideration"),
              required=True, coerce=as_positive_decimal),
        # Required from S7: every comparable is adjusted for the time between its
        # transaction and the valuation date, and that is not computable without it.
        Field("sale_date", ("sale_date", "date", "registration_date"), required=True, coerce=as_date),
        Field("property_type", ("property_type", "type"), coerce=as_optional_text),
        Field("floor", ("floor", "floor_no"), coerce=as_int),
        Field("age_years", ("age_years", "age", "building_age"), coerce=as_int),
        Field("distance_m", ("distance_m", "distance"), coerce=as_non_negative_decimal),
        Field("frontage_ft", ("frontage_ft", "frontage"), coerce=as_non_negative_decimal),
        Field("condition", ("condition",), coerce=as_optional_text),
        Field("view", ("view",), coerce=as_optional_text),
        Field("tenure", ("tenure",), coerce=as_optional_text),
        Field("distressed", ("distressed", "distress_sale"), coerce=as_optional_text),
        Field("source", ("source", "evidence_source"), coerce=as_optional_text),
        Field("note", ("note", "remarks"), coerce=as_optional_text),
    ),
)


LEASE_SCHEDULE = SourceSchema(
    key="lease_schedule",
    label="Lease schedule / rent roll",
    version="2.0",
    signature=("tenant", "tenant_name", "monthly_rent", "lease_start", "lease_end"),
    identity=("unit",),
    fields=(
        Field("unit", ("unit", "unit_no", "flat_no", "shop_no"), required=True, coerce=as_text),
        # A vacant unit has no tenant and no rent. Both stay optional so that a
        # vacancy is data rather than a rejected row.
        Field("tenant", ("tenant", "tenant_name", "lessee"), coerce=as_optional_text),
        Field("area", ("area_sqft", "area", "chargeable_area"), required=True, coerce=as_positive_decimal),
        Field("area_unit", ("area_unit", "unit_of_area"), coerce=as_optional_text, default="sqft"),
        Field("monthly_rent", ("monthly_rent", "rent"), coerce=as_non_negative_decimal, default=0),
        Field("security_deposit", ("security_deposit", "deposit"), coerce=as_non_negative_decimal, default=0),
        Field("lease_start", ("lease_start", "start_date", "commencement"), coerce=as_optional_date),
        Field("lease_end", ("lease_end", "end_date", "expiry"), coerce=as_optional_date),
        Field("lock_in_until", ("lock_in_until", "lock_in"), coerce=as_optional_date),
        Field("escalation_pct", ("escalation_%", "escalation_pct", "increment_pct"),
              coerce=as_non_negative_decimal, default=0),
        Field("status", ("status", "occupancy_status"),
              coerce=one_of("occupied", "vacant", "let", "notice", default="occupied")),
        Field("overdue", ("overdue", "arrears"), coerce=as_non_negative_decimal, default=0),
    ),
)


CONSTRUCTION_STAGES = SourceSchema(
    key="construction_stages",
    label="Construction stages",
    version="2.0",
    signature=("stage", "milestone", "completion_%", "disbursement_amount"),
    identity=("stage",),
    fields=(
        Field("stage", ("stage", "milestone", "stage_name"), required=True, coerce=as_text),
        Field("description", ("description",), coerce=as_optional_text),
        Field("completion_pct", ("completion_%", "completion_pct", "progress_pct"),
              required=True, coerce=as_non_negative_decimal),
        Field("disbursement_amount", ("disbursement_amount", "tranche_amount"),
              coerce=as_non_negative_decimal, default=0),
        Field("disbursement_pct", ("disbursement_%", "disbursement_pct"),
              coerce=as_non_negative_decimal, default=0),
        Field("status", ("status",),
              coerce=one_of("completed", "in progress", "pending", "certified", default="pending")),
        Field("target_date", ("target_date", "planned_date"), coerce=as_optional_date),
        Field("actual_date", ("actual_date", "certified_on"), coerce=as_optional_date),
        Field("certified_by", ("certified_by", "certifier"), coerce=as_optional_text),
        Field("remarks", ("remarks", "note"), coerce=as_optional_text),
    ),
)


PORTFOLIO = SourceSchema(
    key="portfolio",
    label="Portfolio",
    version="2.0",
    signature=("property_id", "property_name", "current_value", "purchase_price"),
    identity=("property_id", "property_name"),
    fields=(
        Field("property_id", ("property_id", "id", "code"), coerce=as_optional_text),
        Field("property_name", ("property_name", "name", "property"), required=True, coerce=as_text),
        Field("property_type", ("property_type", "type", "asset_class"), coerce=as_optional_text),
        Field("locality", ("locality", "location", "city"), coerce=as_optional_text),
        Field("area", ("area_sqft", "area"), coerce=as_positive_decimal),
        Field("area_unit", ("area_unit",), coerce=as_optional_text, default="sqft"),
        Field("current_value", ("current_value", "market_value", "valuation"),
              required=True, coerce=as_non_negative_decimal),
        Field("purchase_price", ("purchase_price", "cost", "acquisition_cost"),
              coerce=as_non_negative_decimal, default=0),
        Field("monthly_rent", ("monthly_rent", "rent"), coerce=as_non_negative_decimal, default=0),
        Field("loan_outstanding", ("loan_outstanding", "mortgage", "debt"),
              coerce=as_non_negative_decimal, default=0),
        Field("occupancy", ("occupancy", "status"), coerce=as_optional_text),
    ),
)


LAND_RECORDS = SourceSchema(
    key="land_records",
    label="Land records",
    version="2.0",
    signature=("survey_no", "sy_no", "khasra_no", "khata", "owner_name"),
    identity=("survey_no", "khata_no"),
    fields=(
        Field("survey_no", ("survey_no", "sy_no", "khasra_no"), required=True, coerce=as_text),
        Field("khata_no", ("khata", "khata_no", "khatauni"), coerce=as_optional_text),
        Field("owner_name", ("owner_name", "owner", "recorded_owner"), coerce=as_optional_text),
        Field("area", ("area", "extent", "area_sqft"), required=True, coerce=as_positive_decimal),
        # The dangerous one. A land record quotes bigha, guntha or katha, and the
        # factor is state-dependent — so the unit and the state are both required
        # rather than assumed. See utils/geo.py.
        Field("area_unit", ("area_unit", "unit", "measure"), required=True, coerce=as_text),
        Field("state", ("state", "state_code"), required=True, coerce=as_text),
        Field("district", ("district",), coerce=as_optional_text),
        Field("land_use", ("land_use", "zoning", "classification"), coerce=as_optional_text),
        Field("encumbrance", ("encumbrance", "ec_status"), coerce=as_optional_text),
        Field("remarks", ("remarks",), coerce=as_optional_text),
    ),
)


ALL_SCHEMAS: tuple[SourceSchema, ...] = (
    COMPARABLES,
    LEASE_SCHEDULE,
    CONSTRUCTION_STAGES,
    PORTFOLIO,
    LAND_RECORDS,
)

SCHEMAS_BY_KEY = {s.key: s for s in ALL_SCHEMAS}
