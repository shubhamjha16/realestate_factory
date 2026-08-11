"""
Valuation calculator node.
"""

from __future__ import annotations

from app.services.graph.state import REState, safe
from app.services.valuation.valuationCalculator import compute as val_compute


def valuation_calculator_node(state: REState) -> dict:
    parsed = safe(state, "parsed_data", {})
    doc_type = safe(state, "doc_type", "")
    if not parsed or not parsed.get("records"):
        return {"computed": {"type": "empty"}}
    try:
        computed = val_compute(parsed, doc_type)
    except ValueError as e:
        return {"computed": {"type": "error", "error": str(e)}, "generation_errors": str(e)}
    return {"computed": computed}
