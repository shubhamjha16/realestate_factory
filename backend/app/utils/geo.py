"""
Area conversion, state-aware.

Factors come from `packages/units/units.json` — the same file the console reads.
Neither app holds a factor of its own, because a console that converts square
metres differently from the engine produces a report whose area and rate
contradict its total.

Two rules make this safe rather than merely convenient:

  1. **`Decimal`, never float.** A rate multiplied by a float-converted area is a
     figure that will not reconcile, and land is quoted in units whose factors
     have five significant digits.
  2. **A state-dependent unit without a state is an error.** A bigha is not one
     area — it differs by state and, within a state, by district. Guessing is
     worse than failing, because a wrong conversion silently multiplies a
     valuation and nothing downstream can tell.

The seeded state factors are the commonly cited ones and are marked
`verified: false`. Using one requires an explicit opt-in. Verifying them against
the notified schedules is §11.2, still unassigned.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

UNITS_FILE = Path(__file__).resolve().parents[3] / "packages" / "units" / "units.json"


class UnknownUnitError(ValueError):
    """The unit is not in the table at all."""


class AmbiguousUnitError(ValueError):
    """
    The unit has no single factor and no jurisdiction was given.

    Raised rather than defaulted. A bigha silently taken as the Uttar Pradesh
    figure when the parcel is in West Bengal overstates it by 87%, and the report
    that carries it looks entirely normal.
    """

    def __init__(self, unit: str, known_states: tuple[str, ...]):
        self.unit = unit
        self.known_states = known_states
        super().__init__(
            f"{unit!r} varies by state and district; a jurisdiction is required. "
            f"Known: {', '.join(known_states) or 'none'}."
        )


class UnverifiedFactorError(ValueError):
    """
    The factor exists but has not been checked against a notified schedule.

    Callable with `allow_unverified=True` for exploratory work; a figure that
    reaches a signed report must not depend on one.
    """

    def __init__(self, unit: str, state: str, source: str):
        self.unit = unit
        self.state = state
        self.source = source
        super().__init__(
            f"the {unit!r} factor for {state} is not verified against a notified "
            f"schedule ({source}). Verify it, or pass allow_unverified=True and "
            f"accept that the figure cannot be relied upon."
        )


@dataclass(frozen=True)
class Factor:
    unit: str
    sqft_per_unit: Decimal
    label: str
    verified: bool
    source: str
    state: str | None = None


@lru_cache(maxsize=1)
def _table() -> dict:
    return json.loads(UNITS_FILE.read_text())


@lru_cache(maxsize=1)
def universal_units() -> tuple[str, ...]:
    return tuple(_table()["universal"])


@lru_cache(maxsize=1)
def state_dependent_units() -> tuple[str, ...]:
    return tuple(_table()["state_dependent"])


def normalise_unit(unit: str) -> str:
    """`Sq. Ft`, `SQFT`, `square feet` and `sq_ft` are all `sqft`."""
    cleaned = unit.strip().lower().replace(".", "").replace("_", " ").replace("-", " ")
    cleaned = " ".join(cleaned.split())
    return _ALIASES.get(cleaned, cleaned.replace(" ", ""))


_ALIASES = {
    "sq ft": "sqft", "sqft": "sqft", "square feet": "sqft", "square foot": "sqft", "ft2": "sqft",
    "sq m": "sqm", "sqm": "sqm", "square metre": "sqm", "square meter": "sqm", "m2": "sqm",
    "sq yd": "sqyd", "sqyd": "sqyd", "square yard": "sqyd", "gaj": "sqyd",
    "acres": "acre", "hectares": "hectare", "ha": "hectare",
    "gunta": "guntha", "gunthas": "guntha",
    "cents": "cent", "grounds": "ground",
    "kanals": "kanal", "marlas": "marla",
    "bighas": "bigha", "biswas": "biswa", "kathas": "katha", "vighas": "vigha",
    "bigha": "bigha", "katha": "katha", "cottah": "katha",
}


def factor_for(unit: str, state: str | None = None, *, allow_unverified: bool = False) -> Factor:
    """
    Resolve one unit to square feet.

    `state` is an ISO-style code (`MH`, `UP`). It is ignored for universal units
    and required for the rest.
    """
    key = normalise_unit(unit)
    table = _table()

    if key in table["universal"]:
        entry = table["universal"][key]
        return Factor(
            unit=key,
            sqft_per_unit=Decimal(entry["sqft_per_unit"]),
            label=entry["label"],
            verified=entry["verified"],
            source=entry["source"],
        )

    if key in table["state_dependent"]:
        by_state = table["state_dependent"][key]["by_state"]
        if state is None:
            raise AmbiguousUnitError(key, tuple(by_state))
        code = state.strip().upper()
        if code not in by_state:
            raise AmbiguousUnitError(key, tuple(by_state))

        entry = by_state[code]
        if not entry["verified"] and not allow_unverified:
            raise UnverifiedFactorError(key, code, entry["source"])
        return Factor(
            unit=key,
            sqft_per_unit=Decimal(entry["sqft_per_unit"]),
            label=table["state_dependent"][key]["label"],
            verified=entry["verified"],
            source=entry["source"],
            state=code,
        )

    raise UnknownUnitError(
        f"unknown area unit {unit!r}. Known: "
        f"{', '.join(sorted(universal_units() + state_dependent_units()))}"
    )


def to_sqft(
    value: Decimal | int | str,
    unit: str,
    state: str | None = None,
    *,
    allow_unverified: bool = False,
) -> Decimal:
    """Exact. No rounding happens here — the caller's policy decides that."""
    return Decimal(str(value)) * factor_for(unit, state, allow_unverified=allow_unverified).sqft_per_unit


def convert(
    value: Decimal | int | str,
    from_unit: str,
    to_unit: str,
    state: str | None = None,
    *,
    allow_unverified: bool = False,
) -> Decimal:
    sqft = to_sqft(value, from_unit, state, allow_unverified=allow_unverified)
    target = factor_for(to_unit, state, allow_unverified=allow_unverified)
    return sqft / target.sqft_per_unit


def is_state_dependent(unit: str) -> bool:
    return normalise_unit(unit) in state_dependent_units()
