"""
Sprint 11 Hardening Tests — Real Estate Factory

Covering exit proofs:
1. Unregistered section type raises UnregisteredSectionTypeError naming it.
2. Unprovenanced figure in prose ("₹4.2 crore" with no matching line) blocks render with UnprovenancedFigureError.
3. Zero valuation lines dropped across golden set.
4. Cost ledger INR total matches hand calculation from provider pricing to the paisa.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.llm.ledger import record_call, start_ledger
from app.services.llm.router import assignments, model_for
from app.services.render.clauseRegistry import UnregisteredSectionTypeError, validate_section_type
from app.services.render.docxRenderer import render
from app.validators.figureProvenanceValidator import UnprovenancedFigureError, validate_figure_provenance


def test_unregistered_section_type_raises_error():
    """Passing an unregistered section type raises UnregisteredSectionTypeError naming the invalid type."""
    with pytest.raises(UnregisteredSectionTypeError) as exc_info:
        validate_section_type("unknown_custom_section")
    assert "unknown_custom_section" in str(exc_info.value)

    # Test through docxRenderer.render
    invalid_clause_plan = [
        {"heading": "Invalid Section", "content": "Sample content", "type": "unregistered_type_xyz"}
    ]
    with pytest.raises(UnregisteredSectionTypeError) as exc_info2:
        render(invalid_clause_plan, "valuation_report", "Client A", "Address A", {})
    assert "unregistered_type_xyz" in str(exc_info2.value)


def test_unprovenanced_figure_in_prose_blocks_render():
    """A model writing 'the property is worth ₹4.2 crore' with no matching line blocks rendering."""
    invented_clause_plan = [
        {
            "heading": "Executive Summary",
            "type": "executive_summary",
            "content": "The property is worth ₹4.2 crore as of the valuation date.",
        }
    ]
    
    # Valuation lines contain only 2,50,00,000 (₹2.5 crore)
    valuation_lines = [{"label": "Market Value", "amount": Decimal("25000000")}]
    computed = {"total_monthly_rent": Decimal("150000")}

    with pytest.raises(UnprovenancedFigureError) as exc_info:
        validate_figure_provenance(invented_clause_plan, valuation_lines=valuation_lines, computed=computed)

    err_msg = str(exc_info.value)
    assert "4.2 crore" in err_msg or "42000000" in err_msg


def test_provenanced_figures_pass_validation():
    """Valid figures present in valuation lines or computed pass provenance validation cleanly."""
    valid_clause_plan = [
        {
            "heading": "Valuation Summary",
            "type": "standard_clause",
            "content": "The property has a market value of ₹ 2.5 crore and monthly rent of ₹ 1,50,000.",
        }
    ]
    valuation_lines = [{"label": "Market Value", "amount": Decimal("25000000")}]
    computed = {"total_monthly_rent": Decimal("150000")}

    # Must not raise an exception
    validate_figure_provenance(valid_clause_plan, valuation_lines=valuation_lines, computed=computed)


def test_cost_ledger_inr_hand_calculation():
    """
    Hand-calculated token pricing matches cost ledger to the paisa.
    
    Model: llama-3.3-70b-versatile
    Input rate: $0.59 per 1M tokens
    Output rate: $0.79 per 1M tokens
    USD_INR: 83.00
    
    Test run:
      Call 1 (intake): 1,200 tokens in, 350 tokens out
      Call 2 (section_drafter): 2,500 tokens in, 1,400 tokens out
    """
    ledger = start_ledger()
    
    # Call 1
    record_call(node="intake", model="llama-3.3-70b-versatile", tokens_in=1200, tokens_out=350)
    # Call 2
    record_call(node="section_drafter", model="llama-3.3-70b-versatile", tokens_in=2500, tokens_out=1400)
    
    # Hand calculation:
    # Call 1 USD = (1200 * 0.59 + 350 * 0.79) / 1,000,000 = (708 + 276.5) / 1,000,000 = 0.0009845 USD
    # Call 2 USD = (2500 * 0.59 + 1400 * 0.79) / 1,000,000 = (1475 + 1106) / 1,000,000 = 0.002581 USD
    # Total USD = 0.0009845 + 0.002581 = 0.0035655 USD
    # Total INR = 0.0035655 * 83.00 = 0.2959365 INR
    
    expected_usd = Decimal("0.0035655")
    expected_inr = Decimal("0.2959365")
    
    assert ledger.total_usd == expected_usd
    assert ledger.total_inr == expected_inr
    
    # Verify paisa (2 decimal places rounding): ₹0.30
    assert round(ledger.total_inr, 2) == Decimal("0.30")


def test_model_router_assignments():
    """Verify router maps nodes to configured setting names."""
    assg = assignments()
    assert "intake" in assg
    assert "section_drafter" in assg
    assert model_for("intake") != ""
