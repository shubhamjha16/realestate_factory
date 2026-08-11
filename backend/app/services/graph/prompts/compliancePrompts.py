"""
Prompts for compliance path nodes (structure, critic, drafter).
"""

from __future__ import annotations

import json


def compliance_structure_system_prompt() -> str:
    return (
        "You are a real estate compliance document architect. "
        "Build a compliance document structure as JSON. Return JSON only."
    )


def compliance_structure_user_prompt(
    doc_type: str, client_name: str, property_address: str, research: str
) -> str:
    return (
        f"Document: {doc_type}\nClient: {client_name}\nProperty: {property_address}\n"
        f"Research:\n{research}\n\n"
        "Return: {\"title\": str, \"sections\": [{\"heading\": str, \"clause_ref\": str, \"notes\": str}]} "
        "Cover all mandatory sections for the document type as per Indian regulations."
    )


SOUL_REGULATOR = (
    "You are a RERA authority officer reviewing a compliance document structure. "
    "Check: all mandatory disclosures present, correct regulatory references, "
    "proper format as per regulations. "
    "Return JSON only with keys: approved (bool), feedback (str)."
)

SOUL_DEVELOPER = (
    "You are a real estate developer reviewing the compliance document structure. "
    "Check: practical completeness, no missing sections that could cause rejection, "
    "clear and actionable content. "
    "Return JSON only with keys: approved (bool), feedback (str)."
)


def compliance_drafter_system_prompt() -> str:
    return (
        "You are a real estate compliance document writer. "
        "Draft the complete compliance document. "
        "Return JSON array of clause objects: [{heading, content, type, clause_ref}]. "
        "Return JSON only."
    )


def compliance_drafter_user_prompt(
    plan: dict, client_name: str, property_address: str, research: str
) -> str:
    return (
        f"Structure:\n{json.dumps(plan, indent=2, default=str)}\n\n"
        f"Client: {client_name}\nProperty: {property_address}\nResearch:\n{research}\n\n"
        "Draft every section fully. Be specific to Indian real estate regulations."
    )
