"""
Agreement drafter node.
"""

from __future__ import annotations

import json

from app.services.graph import llm
from app.services.graph.prompts.agreementPrompts import (
    agreement_drafter_system_prompt,
    agreement_drafter_user_prompt,
)
from app.services.graph.state import REState, safe


def agreement_drafter_node(state: REState) -> dict:
    doc_type = safe(state, "doc_type", "sale_deed")
    client = safe(state, "client_name", "")
    prop = safe(state, "property_address", "")
    research = safe(state, "re_research", "")
    notes = safe(state, "special_notes", "")

    system = agreement_drafter_system_prompt()
    user = agreement_drafter_user_prompt(doc_type, client, prop, notes, research)
    raw = llm.chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=6000,
        json_mode=True,
        node="agreement_drafter",
    )
    try:
        data = json.loads(raw)
        clauses = data if isinstance(data, list) else data.get("clauses", data.get("sections", []))
    except Exception:
        clauses = [{"heading": "Agreement", "content": raw, "type": "standard_clause"}]

    return {"clause_plan": clauses}
