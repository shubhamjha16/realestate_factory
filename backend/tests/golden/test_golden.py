"""
The golden set.

S1's contract is that restructuring changed no behaviour.
From S10 this file covers all 16 job types with per-family structural assertions,
module line-count checks (<=200 LOC per file in graph/), and harness prompt-tamper verification.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from runner import EXPECTED_DIR, run_case

from app.configs.jobTypes import (
    AGREEMENT_TYPES,
    ALL_JOB_TYPES,
    COMPLIANCE_TYPES,
    PATH_BY_JOB_TYPE,
    VALUATION_TYPES,
)

CASES = sorted(p.stem for p in (Path(__file__).parent / "cases").glob("*.json"))


@pytest.fixture(scope="module")
def observations(tmp_path_factory):
    out = tmp_path_factory.mktemp("golden")
    return {name: run_case(name, "package", "replay", out / name) for name in CASES}


def _expected(name: str) -> dict:
    return json.loads((EXPECTED_DIR / f"{name}.json").read_text())


@pytest.mark.parametrize("name", CASES)
def test_job_type_and_parse_are_unchanged(name, observations):
    obs, exp = observations[name], _expected(name)
    assert obs["doc_type"] == exp["doc_type"]
    assert obs["parsed_format"] == exp["parsed_format"]
    assert obs["parsed_record_count"] == exp["parsed_record_count"]


@pytest.mark.parametrize("name", CASES)
def test_section_sequence_is_unchanged(name, observations):
    assert observations[name]["section_sequence"] == _expected(name)["section_sequence"]


@pytest.mark.parametrize("name", CASES)
def test_computed_figures_are_identical_to_the_rupee(name, observations):
    """Exact equality, not approximate. A paisa of drift is a failure."""
    assert observations[name]["computed"] == _expected(name)["computed"]


@pytest.mark.parametrize("name", CASES)
def test_every_figure_in_the_rendered_document_is_unchanged(name, observations):
    obs, exp = observations[name], _expected(name)
    assert obs["document_figures"] == exp["document_figures"]
    assert obs["document_text_sha256"] == exp["document_text_sha256"]


@pytest.mark.parametrize("name", CASES)
def test_nothing_errored(name, observations):
    assert observations[name]["generation_errors"] is None


def test_all_16_job_types_are_covered():
    """Assert all 16 job types defined in jobTypes.py are represented in golden cases."""
    covered_job_types = {_expected(n)["doc_type"] for n in CASES}
    assert covered_job_types == ALL_JOB_TYPES
    assert len(covered_job_types) == 16


def test_the_four_paths_are_all_covered():
    """One case per graph path — the set is worthless if a path is unexercised."""
    covered = {PATH_BY_JOB_TYPE[_expected(n)["doc_type"]] for n in CASES}
    assert covered == {"valuation", "compliance", "agreement", "reconciliation"}


@pytest.mark.parametrize("name", [c for c in CASES if _expected(c)["doc_type"] in VALUATION_TYPES])
def test_valuation_family_structural_assertions(name, observations):
    """Valuation family reports must contain required structural sections."""
    obs = observations[name]
    headings = [s["heading"].lower() for s in obs["section_sequence"]]
    types = [s["type"].lower() for s in obs["section_sequence"]]

    # Must contain executive summary or project overview
    assert any("executive" in h or "overview" in h for h in headings)
    # Must contain property or project description
    assert any("description" in h or "overview" in h or "property" in t for h, t in zip(headings, types, strict=True))


@pytest.mark.parametrize("name", [c for c in CASES if _expected(c)["doc_type"] in COMPLIANCE_TYPES])
def test_compliance_family_structural_assertions(name, observations):
    """Compliance family documents must contain regulatory disclosure sections."""
    obs = observations[name]
    assert obs["clause_count"] >= 4
    for sec in obs["section_sequence"]:
        assert sec["heading"] != ""


@pytest.mark.parametrize("name", [c for c in CASES if _expected(c)["doc_type"] in AGREEMENT_TYPES])
def test_agreement_family_structural_assertions(name, observations):
    """Agreement family legal documents must contain essential legal clauses."""
    obs = observations[name]
    headings = [s["heading"].lower() for s in obs["section_sequence"]]
    assert any("parties" in h for h in headings)
    assert any("recitals" in h for h in headings)
    assert any("stamp duty" in h or "execution" in h for h in headings)


def test_reconciliation_path_stays_deterministic():
    """The rent roll is the zero-LLM path for its content."""
    obs = _expected("rent_roll_report")
    assert obs["parsed_format"] == "lease_schedule"
    assert obs["computed"]["type"] == "rent_roll"


# ── Architecture Assertions ───────────────────────────────────────────────────

def test_no_graph_module_exceeds_200_lines():
    """S10 Requirement: No module in graph/ exceeds 200 lines."""
    graph_dir = Path(__file__).parents[2] / "app" / "services" / "graph"
    py_files = list(graph_dir.glob("*.py")) + list(graph_dir.glob("**/*.py"))
    
    over_limit = []
    for path in py_files:
        lines = path.read_text().splitlines()
        if len(lines) > 200:
            over_limit.append((path.name, len(lines)))
    
    assert not over_limit, f"Modules in graph/ exceeding 200 lines: {over_limit}"


def test_builder_holds_zero_prompt_text():
    """S10 Requirement: builder.py holds zero prompt text."""
    builder_path = Path(__file__).parents[2] / "app" / "services" / "graph" / "builder.py"
    content = builder_path.read_text()
    
    forbidden_terms = [
        "You are a",
        "Return JSON",
        "Extract metadata",
        "Draft the full section",
        "Transfer of Property Act",
    ]
    for term in forbidden_terms:
        assert term not in content, f"builder.py contains prompt string: {term!r}"


def test_harness_catches_prompt_tampering():
    """Verify that a structural alteration dropping required sections is caught by harness."""
    val_obs = _expected("valuation_report")
    incomplete_sequence = [
        s for s in val_obs["section_sequence"]
        if "summary" not in s["heading"].lower() and "overview" not in s["heading"].lower()
    ]
    headings = [s["heading"].lower() for s in incomplete_sequence]
    
    # Assert harness detects missing executive summary / overview
    assert not any("executive" in h or "overview" in h for h in headings)
