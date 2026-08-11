"""
Compliance drafter node.
"""

from __future__ import annotations

import json

from app.services.graph import llm
from app.services.graph.prompts.compliancePrompts import (
    compliance_drafter_system_prompt,
    compliance_drafter_user_prompt,
)
from app.services.graph.state import REState, safe


def compliance_drafter_node(state: REState) -> dict:
    plan = safe(state, "structure_plan", {})
    research = safe(state, "re_research", "")
    client = safe(state, "client_name", "")
    prop = safe(state, "property_address", "")

    system = compliance_drafter_system_prompt()
    user = compliance_drafter_user_prompt(plan, client, prop, research)
    raw = llm.chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=6000,
        json_mode=True,
        node="compliance_drafter",
    )
    try:
        data = json.loads(raw)
        clauses = data if isinstance(data, list) else data.get("clauses", data.get("sections", []))
    except Exception:
        clauses = [{"heading": "Document", "content": raw, "type": "standard_clause"}]

    return {"clause_plan": clauses}
