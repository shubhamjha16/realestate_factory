"""
The evidence check node.

Sits **before the structure nodes**, so a property that cannot support the report
is refused before a single token is spent drafting one. The job terminates as
`blocked_evidence` naming what is missing, and nothing renders.

This is the first node in the graph that can end a job on purpose. That is the
point: a valuation the evidence does not support should not exist, and producing
one and hedging it in the prose is worse than producing nothing, because the
hedge is what a lender skips.

**The node reads, it does not fetch.** `generationService` assembles the bundle
from the database and seeds it on the state before the graph is invoked. Two
reasons: the graph stays synchronous and free of database access, which is what
S10 needs to split it cleanly; and the bundle is built by the service from a
scoped repository call, so it cannot be supplied by a caller. There is no request
field that reaches it.
"""

from __future__ import annotations

from app.utils.logger import get_logger
from app.validators.evidenceValidator import (
    EvidenceBlocked,
    EvidenceBundle,
    check_preflight,
    required_evidence,
)

logger = get_logger(__name__)


def bundle_from_state(summary: dict | None) -> EvidenceBundle | None:
    if not summary:
        return None
    return EvidenceBundle(
        property_id=str(summary.get("property_id", "")),
        document_kinds=frozenset(summary.get("document_kinds", [])),
        title_chain_length=int(summary.get("title_chain_length", 0)),
        title_chain_has_gap=bool(summary.get("title_chain_has_gap", False)),
        encumbrance_count=int(summary.get("encumbrance_count", 0)),
        subsisting_encumbrance_count=int(summary.get("subsisting_encumbrances", 0)),
        approval_kinds=frozenset(summary.get("approvals", [])),
        document_ids_by_kind=summary.get("document_ids_by_kind", {}),
    )


def evidence_check_node(state: dict) -> dict:
    """
    Gate the job on the evidence the property carries.

    A deliverable that asserts facts and has no evidence bundle is blocked, not
    waved through. "No property was attached" is not a reason to skip the check —
    it is the reason the check fails.
    """
    doc_type = state.get("doc_type") or ""
    required = required_evidence(doc_type)

    if not required:
        # Nothing this deliverable asserts needs a record. A rent roll states
        # figures, not facts about title.
        return {"evidence_checked": True, "evidence_missing": None}

    bundle = bundle_from_state(state.get("evidence_bundle"))
    if bundle is None:
        logger.warning(
            "job %s: %s asserts facts but no property evidence is attached",
            state.get("_job_id"), doc_type,
        )
        return {
            "evidence_checked": False,
            "evidence_missing": [
                f"a {doc_type.replace('_', ' ')} asserts facts that must resolve to a "
                f"record, and no property evidence is attached to this job"
            ],
            "generation_errors": (
                f"blocked_evidence: a {doc_type.replace('_', ' ')} asserts facts about a "
                f"property, and no property is attached to this job."
            ),
            "_blocked": True,
        }

    missing = check_preflight(bundle, doc_type)
    if missing:
        blocked = EvidenceBlocked(bundle.property_id, missing)
        logger.warning("job %s blocked on evidence: %s", state.get("_job_id"), blocked)
        return {
            "evidence_checked": False,
            "evidence_missing": [m.describe() for m in missing],
            "generation_errors": str(blocked),
            "_blocked": True,
        }

    return {"evidence_checked": True, "evidence_missing": None}


def evidence_route(state: dict) -> str:
    """`blocked` ends the graph. There is deliberately no edge around it."""
    return "blocked" if state.get("_blocked") else "continue"
