"""
S8's exit proofs — the evidence gate.

  · a valuation for a property with no encumbrance certificate is blocked,
    naming the missing document, and nothing renders
  · "clear and marketable title" with no title chain is blocked
  · a complete property passes, with every assertion linked to a record

The gate has no bypass flag, and `test_the_gate_has_no_bypass` asserts that by
inspecting the signature — the day someone adds `force=True` for a demo, the
build fails.
"""

from __future__ import annotations

import inspect

import pytest

from app.services.graph.nodes.evidenceCheck import evidence_check_node, evidence_route
from app.validators.evidenceValidator import (
    EvidenceBlocked,
    EvidenceBundle,
    EvidenceClass,
    check_preflight,
    enforce,
    required_evidence,
    scan_assertions,
)

COMPLETE = EvidenceBundle(
    property_id="prop-1",
    document_kinds=frozenset({"title_deed", "encumbrance_cert", "plan", "tax_receipt"}),
    title_chain_length=3,
    title_chain_has_gap=False,
    encumbrance_count=1,
    subsisting_encumbrance_count=0,
    approval_kinds=frozenset({"cc", "oc"}),
    document_ids_by_kind={"title_deed": ["d1"], "encumbrance_cert": ["d2"]},
)

NO_EC = EvidenceBundle(
    property_id="prop-2",
    document_kinds=frozenset({"title_deed", "plan"}),
    title_chain_length=3,
)

BARE = EvidenceBundle(property_id="prop-3")


# ── pre-flight ────────────────────────────────────────────────────────────────


def test_a_valuation_without_an_encumbrance_certificate_is_blocked():
    """S8's first exit proof, at the gate rather than at the render."""
    missing = check_preflight(NO_EC, "valuation_report")

    assert len(missing) == 1
    assert missing[0].evidence is EvidenceClass.ENCUMBRANCE_CERT
    described = missing[0].describe()
    assert "encumbrance certificate" in described
    assert "none is on record" in described


def test_the_block_names_everything_missing_not_just_the_first():
    """A valuer sent away three times for one document is a valuer who stops."""
    missing = check_preflight(BARE, "valuation_report")
    kinds = {m.evidence for m in missing}
    assert kinds == {
        EvidenceClass.TITLE_CHAIN,
        EvidenceClass.ENCUMBRANCE_CERT,
        EvidenceClass.AREA_EVIDENCE,
    }


def test_a_complete_property_passes_pre_flight():
    assert check_preflight(COMPLETE, "valuation_report") == []
    enforce(COMPLETE, job_type="valuation_report")


def test_a_title_chain_with_a_gap_is_not_a_chain():
    """A chain missing its middle link cannot support "marketable"."""
    broken = EvidenceBundle(
        property_id="p", title_chain_length=3, title_chain_has_gap=True,
        document_kinds=frozenset({"encumbrance_cert", "plan"}),
    )
    missing = check_preflight(broken, "valuation_report")
    assert any(m.evidence is EvidenceClass.TITLE_CHAIN for m in missing)


def test_a_rent_roll_asserts_no_facts_about_title_and_is_not_gated():
    """Figures, not facts. Gating it would be a gate nobody believes."""
    assert required_evidence("rent_roll_report") == ()
    enforce(BARE, job_type="rent_roll_report")


def test_each_deliverable_requires_what_it_will_actually_assert():
    assert EvidenceClass.TITLE_CHAIN in required_evidence("sale_deed")
    assert EvidenceClass.APPROVAL_CC in required_evidence("construction_disbursement_report")
    assert EvidenceClass.TITLE_DEED in required_evidence("lease_agreement")


# ── the drafted text ──────────────────────────────────────────────────────────


def test_clear_and_marketable_title_with_no_chain_is_blocked():
    """S8's second exit proof."""
    text = (
        "The vendor holds a clear and marketable title to the subject property, "
        "free from all encumbrances."
    )
    missing = scan_assertions(text, BARE)

    kinds = {m.evidence for m in missing}
    assert EvidenceClass.TITLE_CHAIN in kinds
    assert EvidenceClass.ENCUMBRANCE_CERT in kinds
    # The block quotes the sentence the valuer has to deal with.
    assert any("clear and marketable title" in (m.quote or "") for m in missing)


def test_the_same_sentence_passes_when_the_records_exist():
    text = "The vendor holds a clear and marketable title, free from all encumbrances."
    assert scan_assertions(text, COMPLETE) == []


@pytest.mark.parametrize(
    "sentence,evidence",
    [
        ("Title is clear and unencumbered.", EvidenceClass.TITLE_CHAIN),
        ("The property is free from encumbrances.", EvidenceClass.ENCUMBRANCE_CERT),
        ("There are no subsisting charges.", EvidenceClass.ENCUMBRANCE_CERT),
        ("The vendor is the absolute owner of the said premises.", EvidenceClass.TITLE_CHAIN),
        ("The occupancy certificate has been obtained.", EvidenceClass.APPROVAL_OC),
        ("Municipal taxes have been paid to date.", EvidenceClass.TAX_RECEIPT),
    ],
)
def test_each_assertion_pattern_demands_its_record(sentence, evidence):
    missing = scan_assertions(sentence, BARE)
    assert evidence in {m.evidence for m in missing}, sentence


def test_the_scanner_does_not_fire_on_methodology_or_caveats():
    """
    A gate that fires on every occurrence of "title" is a gate that gets turned
    off, and a gate that is off is worse than none because everyone believes it
    is on.
    """
    innocuous = (
        "The scope of this report covers the title documents produced to us. "
        "We have assumed that the title is capable of investigation, and no "
        "encumbrance search has been undertaken by us. This report is subject to "
        "the assumptions and limiting conditions set out below."
    )
    assert scan_assertions(innocuous, BARE) == []


def test_a_repeated_assertion_is_reported_once_per_sentence():
    text = "Title is clear. Elsewhere: title is clear."
    missing = scan_assertions(text, BARE)
    assert len(missing) == 2  # two distinct sentences, not four rule hits


# ── enforcement ───────────────────────────────────────────────────────────────


def test_enforce_raises_with_everything_that_is_missing():
    with pytest.raises(EvidenceBlocked) as excinfo:
        enforce(BARE, job_type="valuation_report", drafted_text="Title is clear and marketable.")

    message = str(excinfo.value)
    assert "blocked_evidence" in message
    assert "chain of title" in message
    assert "encumbrance certificate" in message
    assert "has no bypass" in message
    assert len(excinfo.value.missing) >= 3


def test_the_gate_has_no_bypass():
    """
    Asserted structurally. Adding `force=True` for a demo would change what this
    product is, so it fails the build rather than passing review on a Friday.
    """
    params = set(inspect.signature(enforce).parameters)
    for escape in ("force", "allow_missing", "skip", "override", "bypass", "strict"):
        assert escape not in params, f"enforce() grew a {escape!r} parameter"

    source = inspect.getsource(enforce)
    assert "if not" not in source.split("missing = ")[0], "an early return crept in"


# ── the graph node ────────────────────────────────────────────────────────────


def _state(**overrides) -> dict:
    return {"doc_type": "valuation_report", "_job_id": "job-1", **overrides}


def test_the_node_blocks_and_names_the_missing_document():
    result = evidence_check_node(_state(evidence_bundle={
        "property_id": "prop-2",
        "document_kinds": ["title_deed", "plan"],
        "title_chain_length": 3,
    }))

    assert result["_blocked"] is True
    assert result["evidence_checked"] is False
    assert "encumbrance certificate" in result["generation_errors"]
    assert evidence_route(result) == "blocked"


def test_the_node_blocks_a_job_with_no_property_at_all():
    """
    An absent property is the reason the check fails, not a reason to skip it.
    """
    result = evidence_check_node(_state(evidence_bundle=None))
    assert result["_blocked"] is True
    assert "no property is attached" in result["generation_errors"]


def test_the_node_passes_a_complete_property():
    result = evidence_check_node(_state(evidence_bundle={
        "property_id": "prop-1",
        "document_kinds": ["title_deed", "encumbrance_cert", "plan", "tax_receipt"],
        "title_chain_length": 3,
        "approvals": ["cc", "oc"],
    }))
    assert result["evidence_checked"] is True
    assert result["evidence_missing"] is None
    assert evidence_route(result) == "continue"


def test_the_node_does_not_gate_a_deliverable_that_asserts_no_facts():
    result = evidence_check_node(_state(doc_type="rent_roll_report", evidence_bundle=None))
    assert result["evidence_checked"] is True
    assert not result.get("_blocked")


def test_the_graph_has_no_edge_around_the_gate():
    """
    The structural guarantee: `blocked` goes to END and nowhere else.
    """
    import os

    os.environ.setdefault("GROQ_API_KEY", "test")
    from app.services.graph.reGraph import app

    edges = app.get_graph().edges
    from_gate = [e for e in edges if e.source == "evidence_check"]
    assert from_gate, "the gate is not wired into the graph"

    blocked = [e for e in from_gate if e.data == "blocked"]
    assert blocked, "there is no blocked branch"
    assert all(e.target == "__end__" for e in blocked), "blocked does not end the graph"
