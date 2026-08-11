"""
Valuation structure node.
"""

from __future__ import annotations

import json

from app.services.graph import llm
from app.services.graph.prompts.valuationPrompts import (
    valuation_structure_system_prompt,
    valuation_structure_user_prompt,
)
from app.services.graph.state import REState, safe


def valuation_structure_node(state: REState) -> dict:
    doc_type = safe(state, "doc_type", "valuation_report")
    prop = safe(state, "property_address", "")
    client = safe(state, "client_name", "")
    computed = safe(state, "computed", {})
    research = safe(state, "re_research", "")

    system = valuation_structure_system_prompt()
    user = valuation_structure_user_prompt(doc_type, client, prop, computed, research)
    raw = llm.chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=2500,
        json_mode=True,
        node="valuation_structure",
    )
    try:
        plan = json.loads(raw)
    except Exception:
        plan = {"title": doc_type.replace("_", " ").title(), "sections": []}

    return {
        "structure_plan": plan,
        "structure_attempt": state.get("structure_attempt", 0) + 1,
        "drafted_sections": [],
        "section_index": 0,
    }
