"""
The income capitalisation approach.

NOI and cap rate already existed in the prototype as loose helpers that nothing
consumed — the sprint plan's words were "exist but are not wired to a value
conclusion". This wires them: direct capitalisation and a discounted cash flow,
each producing an indicated value that reconciliation can weigh.

For a tenanted property this is usually the *better* evidence than comparable
sales, because what a buyer purchases is the income stream. A commercial
building let to one tenant on nine years unexpired is not really comparable to
anything; its value is the rent, the covenant and the yield.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.services.valuation.money import (
    ZERO,
    quantize_money,
    quantize_percent,
    safe_divide,
    to_decimal,
)


class IncomeApproachError(ValueError):
    """An income valuation that cannot be defended is refused rather than computed."""


@dataclass(frozen=True)
class OperatingStatement:
    """
    Gross to net, with every deduction visible.

    Nothing is netted off silently. A reviewer checking a cap rate needs to see
    which deductions were made and at what level, because the difference between
    a 7% and an 8% cap rate on ₹1 crore of NOI is ₹1.8 crore of value.
    """

    gross_rent: Decimal
    vacancy_pct: Decimal
    opex_pct: Decimal
    other_income: Decimal = ZERO
    non_recoverable: Decimal = ZERO

    @property
    def effective_gross_income(self) -> Decimal:
        return (self.gross_rent * (Decimal(1) - self.vacancy_pct / Decimal(100))) + self.other_income

    @property
    def operating_expenses(self) -> Decimal:
        return self.effective_gross_income * (self.opex_pct / Decimal(100)) + self.non_recoverable

    @property
    def net_operating_income(self) -> Decimal:
        return self.effective_gross_income - self.operating_expenses

    def to_dict(self) -> dict:
        return {
            "gross_rent": str(quantize_money(self.gross_rent)),
            "vacancy_pct": str(quantize_percent(self.vacancy_pct)),
            "other_income": str(quantize_money(self.other_income)),
            "effective_gross_income": str(quantize_money(self.effective_gross_income)),
            "opex_pct": str(quantize_percent(self.opex_pct)),
            "non_recoverable": str(quantize_money(self.non_recoverable)),
            "operating_expenses": str(quantize_money(self.operating_expenses)),
            "net_operating_income": str(quantize_money(self.net_operating_income)),
        }


@dataclass(frozen=True)
class IncomeApproachResult:
    method: str
    indicated_value: Decimal
    statement: OperatingStatement
    cap_rate_pct: Decimal | None
    rationale: str
    cash_flows: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "method": "income",
            "sub_method": self.method,
            "indicated_value": str(self.indicated_value),
            "cap_rate_pct": str(self.cap_rate_pct) if self.cap_rate_pct is not None else None,
            "operating_statement": self.statement.to_dict(),
            "rationale": self.rationale,
            "cash_flows": self.cash_flows,
        }


def direct_capitalisation(
    statement: OperatingStatement, cap_rate_pct: Decimal | str, *, rationale: str
) -> IncomeApproachResult:
    """
    Value = NOI ÷ cap rate.

    The cap rate carries a rationale because it is the single most consequential
    number in the approach and it is a judgement, not an observation: it comes
    from comparable investment sales, the covenant strength and the unexpired
    term. Stating it without saying where it came from is stating a conclusion
    without its reasoning.
    """
    rate = to_decimal(cap_rate_pct, field="cap_rate_pct")
    if rate <= 0:
        raise IncomeApproachError(
            f"a capitalisation rate of {rate}% is not usable. Value = NOI ÷ rate, "
            f"so a zero or negative rate is an infinite or negative value."
        )
    if not (rationale or "").strip():
        raise IncomeApproachError(
            "the capitalisation rate has no rationale. It is the most consequential "
            "judgement in the approach — a reviewer cannot check a rate whose "
            "derivation is not stated."
        )

    noi = statement.net_operating_income
    if noi <= 0:
        raise IncomeApproachError(
            f"net operating income is {quantize_money(noi)}. A property with no net "
            f"income has no value on the income approach; conclude on another basis "
            f"and say why."
        )

    return IncomeApproachResult(
        method="direct_capitalisation",
        indicated_value=quantize_money(noi / (rate / Decimal(100))),
        statement=statement,
        cap_rate_pct=quantize_percent(rate),
        rationale=rationale,
    )


def discounted_cash_flow(
    statement: OperatingStatement,
    *,
    discount_rate_pct: Decimal | str,
    growth_pct: Decimal | str,
    exit_cap_rate_pct: Decimal | str,
    years: int,
    rationale: str,
) -> IncomeApproachResult:
    """
    Explicit cash flows over `years`, plus a capitalised terminal value.

    The terminal value usually dominates — often two-thirds of the answer — so
    the exit yield deserves as much scrutiny as the discount rate, and the cash
    flows are returned in full rather than collapsed to a total. A DCF whose
    workings are not visible is an assertion with arithmetic attached.
    """
    discount = to_decimal(discount_rate_pct, field="discount_rate_pct")
    growth = to_decimal(growth_pct, field="growth_pct")
    exit_cap = to_decimal(exit_cap_rate_pct, field="exit_cap_rate_pct")

    if discount <= 0:
        raise IncomeApproachError("the discount rate must be greater than zero")
    if exit_cap <= 0:
        raise IncomeApproachError("the exit capitalisation rate must be greater than zero")
    if years < 1:
        raise IncomeApproachError("a discounted cash flow needs at least one year")
    if not (rationale or "").strip():
        raise IncomeApproachError("the discount and exit rates have no rationale")

    noi = statement.net_operating_income
    if noi <= 0:
        raise IncomeApproachError("net operating income is not positive")

    rate = Decimal(1) + discount / Decimal(100)
    grow = Decimal(1) + growth / Decimal(100)

    flows: list[dict] = []
    present_value = ZERO
    cash = noi

    for year in range(1, years + 1):
        cash = cash * grow if year > 1 else cash
        discounted = cash / (rate**year)
        present_value += discounted
        flows.append(
            {
                "year": year,
                "noi": str(quantize_money(cash)),
                "discount_factor": str((Decimal(1) / rate**year).quantize(Decimal("0.000001"))),
                "present_value": str(quantize_money(discounted)),
            }
        )

    # Terminal value: the following year's income capitalised at the exit yield,
    # then discounted back.
    terminal_noi = cash * grow
    terminal_value = terminal_noi / (exit_cap / Decimal(100))
    terminal_pv = terminal_value / (rate**years)
    present_value += terminal_pv

    flows.append(
        {
            "year": f"{years} (terminal)",
            "noi": str(quantize_money(terminal_noi)),
            "exit_value": str(quantize_money(terminal_value)),
            "present_value": str(quantize_money(terminal_pv)),
        }
    )

    implied_cap = safe_divide(noi, present_value)

    return IncomeApproachResult(
        method="discounted_cash_flow",
        indicated_value=quantize_money(present_value),
        statement=statement,
        cap_rate_pct=quantize_percent(implied_cap * 100) if implied_cap is not None else None,
        rationale=(
            f"{rationale} Terminal value is {quantize_percent(terminal_pv / present_value * 100)}% "
            f"of the total, capitalised at {quantize_percent(exit_cap)}%."
        ),
        cash_flows=flows,
    )


def implied_cap_rate(noi: Decimal | str, value: Decimal | str) -> Decimal | None:
    """What a concluded value implies about the yield. A cross-check, not a method."""
    ratio = safe_divide(to_decimal(noi, field="noi"), to_decimal(value, field="value"))
    return None if ratio is None else quantize_percent(ratio * 100)
