"""
State-level jurisdictional data: RERA authority, stamp duty, area conventions.

This is living content with a maintenance cost, not a seeding task — §11.2 of
the sprint plan asks for an owner and a review cadence before S14. S1 holds only
the shape and the states the graph already names, deliberately empty of rates so
that nothing reads a stale number and presents it as current.

S6 consumes `area_units`. S14 consumes the rest.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Jurisdiction:
    code: str
    name: str
    rera_authority: str
    # Populated in S14, each against the notified schedule, with a source and date.
    stamp_duty_pct: str | None = None
    registration_fee_pct: str | None = None
    # Local area units in use, over and above sqft/sqm/acre. Populated in S6.
    local_area_units: tuple[str, ...] = ()


JURISDICTIONS: dict[str, Jurisdiction] = {
    "MH": Jurisdiction("MH", "Maharashtra", "MahaRERA", local_area_units=("guntha", "are")),
    "KA": Jurisdiction("KA", "Karnataka", "K-RERA", local_area_units=("guntha", "cent")),
    "UP": Jurisdiction("UP", "Uttar Pradesh", "UP RERA", local_area_units=("bigha", "biswa")),
    "DL": Jurisdiction("DL", "Delhi", "Delhi RERA", local_area_units=("bigha", "biswa")),
    "TN": Jurisdiction("TN", "Tamil Nadu", "TNRERA", local_area_units=("cent", "ground")),
    "TG": Jurisdiction("TG", "Telangana", "TG RERA", local_area_units=("guntha",)),
    "GJ": Jurisdiction("GJ", "Gujarat", "GujRERA", local_area_units=("vigha",)),
    "HR": Jurisdiction("HR", "Haryana", "HARERA", local_area_units=("bigha", "kanal", "marla")),
    "WB": Jurisdiction("WB", "West Bengal", "WBRERA", local_area_units=("katha", "bigha")),
    "RJ": Jurisdiction("RJ", "Rajasthan", "RERA Rajasthan", local_area_units=("bigha", "biswa")),
}

# A bigha is not one area. It differs by state and, within a state, by district;
# S6 resolves it against the notified factor rather than a single constant.
AMBIGUOUS_LOCAL_UNITS = frozenset({"bigha", "biswa", "katha", "vigha"})
