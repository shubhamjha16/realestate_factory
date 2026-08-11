"""
Section drafter node.
"""

from __future__ import annotations

import json

from app.services.graph import llm
from app.services.graph.prompts.valuationPrompts import (
    section_drafter_system_prompt,
    section_drafter_user_prompt,
)
from app.services.graph.state import REState, safe


def section_drafter_node(state: REState) -> dict:
    plan = safe(state, "structure_plan", {})
    sections = plan.get("sections", [])
    idx = state.get("section_index", 0)
    drafted = list(state.get("drafted_sections") or [])
    computed = safe(state, "computed", {})

    if idx >= len(sections):
        return {"clause_plan": drafted, "section_index": idx}

    sec = sections[idx]
    heading = sec.get("heading", f"Section {idx+1}")
    sec_type = sec.get("type", "standard_clause")
    notes = sec.get("notes", "")

    data_ctx = ""
    if sec_type in ("valuation_approach", "market_analysis"):
        summary_data = {k: v for k, v in computed.items() if "detail" not in k and "properties" not in k}
        data_ctx = f"Computed data:\n{json.dumps(summary_data, indent=2, default=str)}\n"

    system = section_drafter_system_prompt()
    user = section_drafter_user_prompt(
        heading=heading,
        sec_type=sec_type,
        notes=notes,
        data_ctx=data_ctx,
        property_address=safe(state, "property_address", ""),
        client_name=safe(state, "client_name", ""),
        research_snippet=safe(state, "re_research", "")[:1000],
    )
    raw = llm.chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=2000,
        json_mode=True,
        node="section_drafter",
    )
    try:
        section_obj = json.loads(raw)
    except Exception:
        section_obj = {"heading": heading, "content": raw, "type": sec_type}

    drafted.append(section_obj)
    return {"drafted_sections": drafted, "section_index": idx + 1, "clause_plan": drafted}
