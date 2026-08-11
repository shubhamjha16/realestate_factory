"""
Reconciliation path renderer node (deterministic, zero LLM).
"""

from __future__ import annotations

import json
from decimal import Decimal

from app.services.graph.state import REState, safe
from app.services.valuation.money import format_inr, try_decimal


def _money(computed: dict, key: str) -> str:
    return format_inr(try_decimal(computed.get(key, "0"), Decimal(0)))


def _num(record: dict, key: str) -> str:
    value = try_decimal(record.get(key, "0"), Decimal(0))
    return format_inr(value)


def rec_renderer_node(state: REState) -> dict:
    computed = safe(state, "computed", {})
    client = safe(state, "client_name", "Client")
    prop = safe(state, "property_address", "")
    clauses = []

    if computed.get("type") == "rent_roll":
        clauses = [
            {"heading": "Rent Roll Summary", "type": "summary_table", "content":
                f"Property: {prop}\nClient: {client}\n"
                f"Total Units: {computed.get('total_units',0)} | "
                f"Occupied: {computed.get('occupied_units',0)} | "
                f"Vacant: {computed.get('vacant_units',0)}\n"
                f"Vacancy Rate: {computed.get('vacancy_rate_pct',0)}%\n"
                f"Total Monthly Rent: {_money(computed, 'total_monthly_rent')}\n"
                f"Total Annual Rent: {_money(computed, 'total_annual_rent')}\n"
                f"Total Security Deposit: {_money(computed, 'total_security_deposit')}\n"
                f"Total Overdue: {_money(computed, 'total_overdue')}"},
            {"heading": "Unit-wise Details", "type": "unit_table",
             "content": _format_units(computed.get("unit_details", []))},
            {"heading": "Upcoming Escalations", "type": "standard_clause",
             "content": _format_escalations(computed.get("upcoming_escalations", []))},
        ]
    elif computed.get("type") == "portfolio":
        clauses = [
            {"heading": "Portfolio Summary", "type": "summary_table", "content":
                f"Client: {client}\n"
                f"Total Properties: {computed.get('total_properties',0)}\n"
                f"Total Portfolio Value: {_money(computed, 'total_portfolio_value')}\n"
                f"Total Cost: {_money(computed, 'total_cost')}\n"
                f"Total Equity: {_money(computed, 'total_equity')}\n"
                f"Loan Outstanding: {_money(computed, 'total_loan_outstanding')}\n"
                f"Annual Rental Income: {_money(computed, 'annual_rental_income')}\n"
                f"Portfolio Yield: {computed.get('portfolio_yield_pct',0)}%\n"
                f"Appreciation: {computed.get('appreciation_pct',0)}%"},
            {"heading": "Property-wise Breakdown", "type": "unit_table",
             "content": _format_portfolio(computed.get("properties", []))},
        ]
    else:
        clauses = [{"heading": "Report", "type": "standard_clause",
                    "content": json.dumps(computed, indent=2, default=str)}]

    return {"clause_plan": clauses}


def _format_units(units: list) -> str:
    if not units:
        return "No units found."
    lines = ["Unit | Tenant | Area | Monthly Rent | Status | Overdue"]
    for u in units:
        lines.append(
            f"{u.get('unit','')} | {u.get('tenant','')} | "
            f"{u.get('area_sqft',0)} sqft | {_num(u, 'monthly_rent')} | "
            f"{u.get('status','')} | {_num(u, 'overdue')}"
        )
    return "\n".join(lines)


def _format_escalations(esc: list) -> str:
    if not esc:
        return "No upcoming escalations."
    lines = ["Unit | Tenant | Current Rent | New Rent | Escalation%"]
    for e in esc:
        lines.append(
            f"{e.get('unit','')} | {e.get('tenant','')} | "
            f"{_num(e, 'current_rent')} | {_num(e, 'new_rent')} | "
            f"{e.get('escalation_pct',0)}%"
        )
    return "\n".join(lines)


def _format_portfolio(props: list) -> str:
    if not props:
        return "No properties found."
    lines = ["Property | Type | Area | Value | Monthly Rent | Loan"]
    for p in props:
        lines.append(
            f"{p.get('property_name','')} | {p.get('property_type','')} | "
            f"{p.get('area_sqft',0)} sqft | {_num(p, 'current_value')} | "
            f"{_num(p, 'monthly_rent')} | {_num(p, 'loan_outstanding')}"
        )
    return "\n".join(lines)
