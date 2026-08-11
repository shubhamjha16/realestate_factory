"""
Renderer node with figure provenance enforcement.
"""

from __future__ import annotations

from app.services.graph.state import REState, safe
from app.services.render.docxRenderer import render
from app.validators.figureProvenanceValidator import UnprovenancedFigureError, validate_figure_provenance


def renderer_node(state: REState) -> dict:
    clause_plan = safe(state, "clause_plan", [])
    valuation_lines = safe(state, "valuation_lines")
    computed = safe(state, "computed", {})
    raw_instructions = safe(state, "raw_instructions", "")

    # S11: Enforce figure provenance — no number in prose unless backed by lines or computed records
    try:
        validate_figure_provenance(clause_plan, valuation_lines=valuation_lines, computed=computed, raw_instructions=raw_instructions)
    except UnprovenancedFigureError as err:
        return {
            "doc_path": None,
            "render_error": str(err),
            "render_attempt": state.get("render_attempt", 0) + 1,
        }

    try:
        path = render(
            clause_plan=clause_plan,
            doc_type=safe(state, "doc_type", "valuation_report"),
            client_name=safe(state, "client_name", "Client"),
            property_address=safe(state, "property_address", ""),
            computed=computed,
            header_image_path=safe(state, "header_image_path"),
            job_id=state["_job_id"],
        )
        return {"doc_path": path, "render_error": None}
    except Exception as e:
        return {"doc_path": None, "render_error": str(e), "render_attempt": state.get("render_attempt", 0) + 1}
