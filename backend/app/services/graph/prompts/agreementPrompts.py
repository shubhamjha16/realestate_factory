"""
Prompts for agreement path node.
"""

from __future__ import annotations


def agreement_drafter_system_prompt() -> str:
    return (
        "You are a real estate legal document drafter. "
        "Draft the complete agreement/deed with all clauses. "
        "Return JSON array: [{heading, content, type}]. Return JSON only."
    )


def agreement_drafter_user_prompt(
    doc_type: str, client_name: str, property_address: str, special_notes: str, research: str
) -> str:
    return (
        f"Document: {doc_type}\nParties: {client_name}\nProperty: {property_address}\n"
        f"Special notes: {special_notes}\nResearch:\n{research}\n\n"
        "Draft all standard clauses per Indian law (Transfer of Property Act, Registration Act, Stamp Act). "
        "Include: recitals, consideration, property description, representations, "
        "conditions, covenants, stamp duty note, execution block."
    )
