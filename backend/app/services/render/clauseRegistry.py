"""
Clause registry — Real Estate Factory.

Enforces section type registration. An unregistered section type raises an
explicit `UnregisteredSectionTypeError` rather than falling through to a
generic paragraph.
"""

from __future__ import annotations


class UnregisteredSectionTypeError(ValueError):
    """Raised when a clause plan section type is not registered in the clause registry."""
    pass


# Map of registered section types to renderer function names in docxRenderer
REGISTERED_SECTION_TYPES: set[str] = {
    "summary_table",
    "unit_table",
    "executive_summary",
    "property_description",
    "market_analysis",
    "valuation_approach",
    "due_diligence_check",
    "construction_stage",
    "recommendations",
    "conclusion",
    "standard_clause",
    "numbered_clause",
}


def validate_section_type(section_type: str) -> None:
    """Raise UnregisteredSectionTypeError if section_type is not registered."""
    if section_type not in REGISTERED_SECTION_TYPES:
        raise UnregisteredSectionTypeError(
            f"Unregistered section type {section_type!r}. Must be one of: "
            f"{', '.join(sorted(REGISTERED_SECTION_TYPES))}."
        )
