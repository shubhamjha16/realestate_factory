"""
The golden set.

S1's contract is that restructuring changed no behaviour. These tests hold the
observations recorded against the pre-S1 flat modules and assert the package
reproduces them: same job type, same section sequence, same computed figures to
the rupee, same rendered document.

From S10 this file grows to one fixture per job type with per-family structural
assertions. Every defect found from S21 adds a fixture.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from runner import EXPECTED_DIR, run_case

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


def test_the_four_paths_are_all_covered():
    """One case per graph path — the set is worthless if a path is unexercised."""
    from app.configs.jobTypes import PATH_BY_JOB_TYPE

    covered = {PATH_BY_JOB_TYPE[_expected(n)["doc_type"]] for n in CASES}
    assert covered == {"valuation", "compliance", "agreement", "reconciliation"}


def test_reconciliation_path_stays_deterministic():
    """
    The rent roll is the zero-LLM path for its *content*. Intake and research
    still call the router before the split, so this pins the call count: if a
    future change adds a model call to the reconciliation branch, this fails.
    """
    obs = _expected("rent_roll_report")
    assert obs["parsed_format"] == "lease_schedule"
    assert obs["computed"]["type"] == "rent_roll"
