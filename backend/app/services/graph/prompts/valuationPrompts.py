"""
Prompts for valuation path nodes (structure, critic, section drafter).
"""

from __future__ import annotations

import json

# Comprehensive IBBI / RICS reporting checklist sections:
IBBI_RICS_CHECKLIST_SECTIONS = (
    "scope_and_purpose",
    "basis_and_premise",
    "property_description",
    "market_commentary",
    "valuation_approach",
    "adjustment_grid",
    "reconciliation",
    "assumptions_and_limiting_conditions",
    "valuer_declaration",
)


def valuation_structure_system_prompt() -> str:
    return (
        "You are a real estate report architect. "
        "Build a structured report outline as a JSON object. Return JSON only."
    )


def valuation_structure_user_prompt(
    doc_type: str, client_name: str, property_address: str, computed: dict, research: str
) -> str:
    computed_summary = {
        k: v for k, v in computed.items()
        if "detail" not in k and "properties" not in k
    }
    return (
        f"Document: {doc_type}\nClient: {client_name}\nProperty: {property_address}\n"
        f"Computed data: {json.dumps(computed_summary, indent=2, default=str)}\n"
        f"Research:\n{research}\n\n"
        "Return: {\"title\": str, \"sections\": [{\"heading\": str, \"type\": str, \"notes\": str}]} "
        "For valuation_report include: Executive Summary, Property Description, "
        "Location Analysis, Market Analysis, Sales Comparison Approach, "
        "Income Approach, Cost Approach, Reconciliation of Value, Conclusion & Certificate. "
        "For due_diligence_report include: Executive Summary, Property Description, "
        "Title Chain Analysis, Encumbrance Review, Approvals & Permissions, "
        "Litigation Search, Zoning & Land Use, Risk Summary, Recommendations. "
        "For construction_disbursement_report include: Executive Summary, Project Overview, "
        "Stage-wise Progress, Disbursement Eligibility, Outstanding Tranches, Recommendations. "
        "section type: executive_summary, property_description, market_analysis, "
        "valuation_approach, due_diligence_check, construction_stage, recommendations, conclusion."
    )


SOUL_VALUER = (
    "You are a registered valuer (IBBI) reviewing a real estate report structure. "
    "Check: correct valuation methodology, adequate market evidence, "
    "regulatory compliance (RERA, Companies Act for valuations), completeness. "
    "Return JSON only with keys: approved (bool), feedback (str)."
)

SOUL_CLIENT = (
    "You are a property buyer/bank reviewing the report structure for clarity and usability. "
    "Check: clear conclusion, actionable risk summary, easy navigation, "
    "sufficient supporting data. "
    "Return JSON only with keys: approved (bool), feedback (str)."
)


def section_drafter_system_prompt() -> str:
    return (
        "You are a real estate document writer. "
        "Draft this section in professional language. "
        "Return JSON only with keys: heading (str), content (str), type (str)."
    )


def section_drafter_user_prompt(
    heading: str,
    sec_type: str,
    notes: str,
    data_ctx: str,
    property_address: str,
    client_name: str,
    research_snippet: str,
) -> str:
    return (
        f"Section: {heading}\nType: {sec_type}\nNotes: {notes}\n{data_ctx}"
        f"Property: {property_address}\n"
        f"Client: {client_name}\n"
        f"Research:\n{research_snippet}\n\n"
        "Draft the full section. For valuation sections include specific figures, "
        "methodology explanation, and conclusions. Return JSON."
    )
