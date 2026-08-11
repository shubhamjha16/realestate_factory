"""
The graph's state.

One TypedDict, and the one helper every node uses. Kept apart from the nodes so
that adding a field is a change to a schema rather than an edit inside an
800-line module — which is what S10 exists to end.

Keys prefixed with `_` are internal to a run: the job id, the tenancy scope, and
the flags the routers read. Nothing a caller sends reaches them.
"""

from __future__ import annotations

from typing import Any, TypedDict


class REState(TypedDict, total=False):
    # ── input ────────────────────────────────────────────────────────────────
    raw_instructions: str
    raw_property_data: str
    job_type: str | None
    _job_id: str

    # ── intake ───────────────────────────────────────────────────────────────
    doc_type: str | None
    client_name: str | None
    property_address: str | None
    property_type: str | None
    purpose: str | None
    special_notes: str | None

    # ── property data ────────────────────────────────────────────────────────
    parsed_data: dict | None
    computed: dict | None

    # ── tenancy and subject (S5, S8) ─────────────────────────────────────────
    property_id: str | None
    _scope: Any | None

    # ── evidence gate (S8) ───────────────────────────────────────────────────
    evidence_checked: bool
    evidence_bundle: dict | None
    evidence_missing: list[str] | None
    _blocked: bool

    # ── valuation engine (S11) ───────────────────────────────────────────────
    # Every figure that may be rendered. `figureProvenanceValidator` compares
    # rendered output against these and blocks anything else.
    valuation_lines: list[dict] | None
    valuation_summary: dict | None
    valuation_error: str | None

    # ── research and letterhead ──────────────────────────────────────────────
    re_research: str | None
    header_image_path: str | None

    # ── structure / critic loop ──────────────────────────────────────────────
    structure_plan: dict | None
    structure_attempt: int
    critic_feedback: str | None
    _critic_approved: bool

    # ── section drafter loop ─────────────────────────────────────────────────
    section_index: int
    drafted_sections: list[dict] | None

    # ── renderer ─────────────────────────────────────────────────────────────
    clause_plan: list[dict] | None
    render_attempt: int
    render_error: str | None

    # ── cost ledger (S11) ────────────────────────────────────────────────────
    cost_entries: list[dict] | None

    # ── output ───────────────────────────────────────────────────────────────
    doc_path: str | None
    doc_url: str | None
    generation_errors: str | None


def safe(state: REState | dict, key: str, default: Any = None) -> Any:
    """
    `state.get(key) or default`.

    Deliberately falsy-checking rather than None-checking: the prototype relied
    on an empty string and an absent key behaving the same, and changing that
    now would move figures in the golden set for no benefit.
    """
    return state.get(key) or default  # type: ignore[union-attr]
