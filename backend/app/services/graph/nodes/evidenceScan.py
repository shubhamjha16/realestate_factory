"""
Evidence scan node.
"""

from __future__ import annotations

from app.services.graph.state import REState, safe
from app.validators.evidenceValidator import EvidenceBundle, scan_assertions


def evidence_scan_node(state: REState) -> dict:
    clauses = safe(state, "clause_plan", [])
    summary = state.get("evidence_bundle")
    if not clauses or not summary:
        return {}

    bundle = EvidenceBundle(
        property_id=summary.get("property_id", ""),
        document_kinds=frozenset(summary.get("document_kinds", [])),
        title_chain_length=summary.get("title_chain_length", 0),
        title_chain_has_gap=summary.get("title_chain_has_gap", False),
        subsisting_encumbrance_count=summary.get("subsisting_encumbrances", 0),
        approval_kinds=frozenset(summary.get("approvals", [])),
        document_ids_by_kind=summary.get("document_ids_by_kind", {}),
    )

    drafted = "\n\n".join(str(c.get("content", "")) for c in clauses)
    missing = scan_assertions(drafted, bundle)
    if not missing:
        return {}

    described = [m.describe() for m in missing]
    return {
        "evidence_missing": described,
        "generation_errors": (
            "blocked_evidence: the draft asserts facts with nothing behind them.\n"
            + "\n".join(f"  · {d}" for d in described)
        ),
        "_blocked": True,
    }
