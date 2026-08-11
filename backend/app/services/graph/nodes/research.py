"""
Research node.
"""

from __future__ import annotations

from app.services.graph import llm
from app.services.graph.prompts.researchPrompts import research_system_prompt, research_user_prompt
from app.services.graph.state import REState, safe


def research_node(state: REState) -> dict:
    doc_type = safe(state, "doc_type", "valuation_report")
    prop = safe(state, "property_address", "the subject property")
    computed = safe(state, "computed", {})

    system = research_system_prompt()
    user = research_user_prompt(doc_type, prop, computed)
    research = llm.chat([{"role": "system", "content": system}, {"role": "user", "content": user}], node="research")
    return {"re_research": research}
