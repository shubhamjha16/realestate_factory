"""
Idempotency keys. No infrastructure needed — this is pure function behaviour.

The property that matters: the same intent from the same firm produces the same
key, and anything that changes the intent, or the firm, produces a different one.
"""

from __future__ import annotations

import uuid

from app.utils.idempotency import build_key, checksum_text, normalise_text

FIRM_A = uuid.UUID("11111111-1111-1111-1111-111111111111")
FIRM_B = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _key(**overrides) -> str:
    base = {
        "firm_id": FIRM_A,
        "job_type": "valuation_report",
        "instructions": "Value Plot 14, Sector 62, Noida for loan security",
        "import_checksums": ["abc123"],
    }
    return build_key(**{**base, **overrides})


def test_the_same_submission_produces_the_same_key():
    assert _key() == _key()


def test_whitespace_and_case_are_not_intent():
    """A re-paste with a trailing newline meant the same thing."""
    assert _key(instructions="  Value  Plot 14, Sector 62, Noida FOR loan security \n") == _key(
        instructions="Value Plot 14, Sector 62, Noida for loan security"
    )


def test_a_changed_figure_is_a_different_job():
    """
    Normalisation must not touch digits or punctuation. "12,00,000" and "1200000"
    are different instructions, and collapsing them would return the wrong
    deliverable for the second.
    """
    a = _key(instructions="value at 12,00,000")
    b = _key(instructions="value at 1200000")
    assert a != b


def test_a_different_firm_is_always_a_different_job():
    """
    The firm is in the hash. Two firms submitting byte-identical instructions are
    two jobs; collapsing them would hand one firm's deliverable to another.
    """
    assert _key(firm_id=FIRM_A) != _key(firm_id=FIRM_B)


def test_a_different_job_type_is_a_different_job():
    assert _key(job_type="valuation_report") != _key(job_type="due_diligence_report")


def test_different_imports_are_a_different_job():
    assert _key(import_checksums=["abc123"]) != _key(import_checksums=["def456"])
    assert _key(import_checksums=[]) != _key(import_checksums=["abc123"])


def test_import_order_is_not_intent():
    assert _key(import_checksums=["a", "b"]) == _key(import_checksums=["b", "a"])


def test_field_boundaries_cannot_be_forged():
    """
    Fields are joined on NUL, which cannot appear in an instruction typed into a
    browser. Without a separator, a job_type ending in the first characters of an
    instruction would collide with a shorter type and a longer instruction.
    """
    a = build_key(firm_id=FIRM_A, job_type="mou", instructions="x", import_checksums=[])
    b = build_key(firm_id=FIRM_A, job_type="mo", instructions="ux", import_checksums=[])
    assert a != b


def test_the_key_is_a_full_sha256_hex_digest():
    key = _key()
    assert len(key) == 64
    assert set(key) <= set("0123456789abcdef")


def test_normalisation_is_idempotent():
    once = normalise_text("  Ardhika   Estates\tLLP\n")
    assert normalise_text(once) == once


def test_checksums_differ_for_differing_payloads():
    assert checksum_text("unit,rent\nG-01,100") != checksum_text("unit,rent\nG-01,101")
