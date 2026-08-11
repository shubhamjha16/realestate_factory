"""
Healer node.
"""

from __future__ import annotations

import json

from app.services.graph import llm
from app.services.graph.prompts.healerPrompts import healer_system_prompt, healer_user_prompt
from app.services.graph.state import REState, safe


def healer_node(state: REState) -> dict:
    error = state.get("render_error") or ""
    clauses = safe(state, "clause_plan", [])
    system = healer_system_prompt()
    user = healer_user_prompt(error, clauses)
    raw = llm.chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=4000,
        json_mode=True,
        node="healer",
    )
    try:
        data = json.loads(raw)
        fixed = data if isinstance(data, list) else data.get("clauses", clauses)
    except Exception:
        fixed = clauses
    return {"clause_plan": fixed, "render_error": None}
