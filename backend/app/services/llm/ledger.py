"""
The cost ledger.

One entry per model call, priced from a table of provider rates. The plan's exit
proof for S11 is that a run's rupee figure can be **hand-calculated from provider
pricing and matched to this ledger to the paisa** — so prices are exact
`Decimal`s per million tokens, and nothing here uses float.

Entries accumulate in a run-scoped buffer and are flushed to `cost_entries` by
the caller that owns the job. The buffer exists because the graph is synchronous
and has no database session; making it write directly would put async I/O back
inside a node, which is what S10 just removed.
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass, field
from decimal import Decimal

# USD per million tokens, as published. `USD_INR` is the rate the ledger books
# at; a real deployment sets it from the day's rate and records which.
PRICING: dict[str, tuple[Decimal, Decimal]] = {
    # model: (input per 1M, output per 1M)
    "llama-3.3-70b-versatile": (Decimal("0.59"), Decimal("0.79")),
    "claude-sonnet-4-5": (Decimal("3.00"), Decimal("15.00")),
}
DEFAULT_PRICE = (Decimal("0"), Decimal("0"))

USD_INR = Decimal("83.00")
MILLION = Decimal("1000000")


@dataclass
class CostEntry:
    node: str
    model: str
    tokens_in: int
    tokens_out: int
    usd_cost: Decimal
    inr_cost: Decimal

    def to_dict(self) -> dict:
        return {
            "node": self.node,
            "model": self.model,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "usd_cost": str(self.usd_cost),
            "inr_cost": str(self.inr_cost),
        }


@dataclass
class Ledger:
    entries: list[CostEntry] = field(default_factory=list)

    @property
    def total_inr(self) -> Decimal:
        return sum((e.inr_cost for e in self.entries), Decimal("0"))

    @property
    def total_usd(self) -> Decimal:
        return sum((e.usd_cost for e in self.entries), Decimal("0"))

    def to_dicts(self) -> list[dict]:
        return [e.to_dict() for e in self.entries]


_current: contextvars.ContextVar[Ledger | None] = contextvars.ContextVar(
    "cost_ledger", default=None
)


def price_call(model: str, tokens_in: int, tokens_out: int) -> tuple[Decimal, Decimal]:
    """
    Exact. No rounding until the caller asks for it.

    Rounding per call and then summing is how a ledger stops matching a
    hand-calculation — the same failure S6 fixed for valuations, in a different
    place.
    """
    in_rate, out_rate = PRICING.get(model, DEFAULT_PRICE)
    usd = (Decimal(tokens_in) * in_rate + Decimal(tokens_out) * out_rate) / MILLION
    return usd, usd * USD_INR


def start_ledger() -> Ledger:
    ledger = Ledger()
    _current.set(ledger)
    return ledger


def current_ledger() -> Ledger | None:
    return _current.get()


def record_call(*, node: str, model: str, tokens_in: int, tokens_out: int) -> CostEntry | None:
    """
    Book one call. A no-op when no ledger is open — a golden replay makes no
    calls to price, and a unit test should not need to open one.
    """
    ledger = _current.get()
    usd, inr = price_call(model, tokens_in, tokens_out)
    entry = CostEntry(node, model, tokens_in, tokens_out, usd, inr)
    if ledger is not None:
        ledger.entries.append(entry)
    return entry
