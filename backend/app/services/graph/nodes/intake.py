"""
Intake node.
"""

from __future__ import annotations

import json

from app.services.graph import llm
from app.services.graph.prompts.intakePrompts import intake_system_prompt
from app.services.graph.state import REState


def intake_node(state: REState) -> dict:
    system = intake_system_prompt()
    raw = llm.chat(
        [{"role": "system", "content": system}, {"role": "user", "content": state["raw_instructions"]}],
        json_mode=True,
        node="intake",
    )
    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = {}

    doc_type = parsed.get("doc_type") or state.get("job_type") or "valuation_report"
    return {
        "doc_type": doc_type,
        "client_name": parsed.get("client_name"),
        "property_address": parsed.get("property_address"),
        "property_type": parsed.get("property_type"),
        "purpose": parsed.get("purpose"),
        "special_notes": parsed.get("special_notes"),
    }
