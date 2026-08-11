"""
Graph routing decision functions.
"""

from __future__ import annotations

from app.configs import jobTypes as config
from app.configs.envConfig import settings
from app.services.graph.nodes.evidenceCheck import evidence_route
from app.services.graph.state import REState, safe


def gated_route(state: REState) -> str:
    """The evidence gate and path choice in one decision."""
    if evidence_route(state) == "blocked":
        return "blocked"
    return vision_route(state)


def vision_route(state: REState) -> str:
    doc_type = safe(state, "doc_type", "")
    if doc_type in config.RECONCILIATION_TYPES:
        return "rec_renderer"
    if doc_type in config.VALUATION_TYPES:
        return "valuation_structure"
    if doc_type in config.COMPLIANCE_TYPES:
        return "compliance_structure"
    return "agreement_drafter"


def valuation_critic_route(state: REState) -> str:
    if state.get("_critic_approved"):
        return "section_drafter"
    if state.get("structure_attempt", 0) >= settings.MAX_CRITIC_RETRIES:
        return "section_drafter"
    return "valuation_structure"


def section_drafter_route(state: REState) -> str:
    plan = safe(state, "structure_plan", {})
    sections = plan.get("sections", [])
    idx = state.get("section_index", 0)
    return "section_drafter" if idx < len(sections) else "renderer"


def compliance_critic_route(state: REState) -> str:
    if state.get("_critic_approved"):
        return "compliance_drafter"
    if state.get("structure_attempt", 0) >= settings.MAX_CRITIC_RETRIES:
        return "compliance_drafter"
    return "compliance_structure"


def evidence_scan_route(state: REState) -> str:
    return "blocked" if state.get("_blocked") else "renderer"


def renderer_route(state: REState) -> str:
    if state.get("render_error") and state.get("render_attempt", 0) < settings.MAX_HEALER_RETRIES:
        return "healer"
    return "upload"
