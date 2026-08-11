"""
Valuation critic node.
"""

from __future__ import annotations

import json

from app.services.graph import llm
from app.services.graph.prompts.valuationPrompts import SOUL_CLIENT, SOUL_VALUER
from app.services.graph.state import REState, safe


def valuation_critic_node(state: REState) -> dict:
    plan = safe(state, "structure_plan", {})
    research = safe(state, "re_research", "")

    def _review(soul: str) -> dict:
        user_content = f"Plan:\n{json.dumps(plan, indent=2, default=str)}\n\nContext:\n{research}"
        raw = llm.chat(
            [{"role": "system", "content": soul}, {"role": "user", "content": user_content}],
            max_tokens=600,
            json_mode=True,
            node="valuation_critic",
        )
        try:
            return json.loads(raw)
        except Exception:
            return {"approved": True, "feedback": ""}

    r1 = _review(SOUL_VALUER)
    r2 = _review(SOUL_CLIENT)
    approved = r1.get("approved", True) and r2.get("approved", True)
    feedback = f"Valuer: {r1.get('feedback','')} | Client: {r2.get('feedback','')}"
    return {"_critic_approved": approved, "critic_feedback": feedback}
