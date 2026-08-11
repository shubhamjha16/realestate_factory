"""
Prompts for research node.
"""

from __future__ import annotations

import json


def research_system_prompt() -> str:
    return "You are a senior real estate consultant. Provide concise reference guidance for drafting the document. 3-4 paragraphs max."


def research_user_prompt(doc_type: str, property_address: str, computed: dict) -> str:
    summary_data = {
        k: v for k, v in computed.items()
        if k not in ("unit_details", "stage_details", "properties")
    }
    return (
        f"Document type: {doc_type}\nProperty: {property_address}\n"
        f"Computed data summary: {json.dumps(summary_data, indent=2, default=str)}\n"
        "Provide: applicable regulations (RERA, Transfer of Property Act, Registration Act, Stamp Duty), "
        "market context, standard methodologies (Sales Comparison, Income, Cost approach), "
        "due diligence checklist items, and key clauses for the document type."
    )
