"""
Compliance structure node.
"""

from __future__ import annotations

import json

from app.services.graph import llm
from app.services.graph.prompts.compliancePrompts import (
    compliance_structure_system_prompt,
    compliance_structure_user_prompt,
)
from app.services.graph.state import REState, safe


def compliance_structure_node(state: REState) -> dict:
    doc_type = safe(state, "doc_type", "rera_registration")
    client = safe(state, "client_name", "")
    prop = safe(state, "property_address", "")
    research = safe(state, "re_research", "")

    system = compliance_structure_system_prompt()
    user = compliance_structure_user_prompt(doc_type, client, prop, research)
    raw = llm.chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=2000,
        json_mode=True,
        node="compliance_structure",
    )
    try:
        plan = json.loads(raw)
    except Exception:
        plan = {"title": doc_type.replace("_", " ").title(), "sections": []}

    return {"structure_plan": plan, "structure_attempt": state.get("structure_attempt", 0) + 1}
