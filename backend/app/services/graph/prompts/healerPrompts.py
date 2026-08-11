"""
Prompts for healer node.
"""

from __future__ import annotations

import json


def healer_system_prompt() -> str:
    return (
        "You are a document repair agent. "
        "Given a render error and the clause plan, return a corrected clause plan as JSON array. "
        "Return JSON only."
    )


def healer_user_prompt(error: str, clauses: list) -> str:
    sample_clauses = json.dumps(clauses[:3], indent=2, default=str)
    return (
        f"Error:\n{error}\n\nClause plan (first 3):\n{sample_clauses}\n\n"
        "Return corrected full clause plan."
    )
