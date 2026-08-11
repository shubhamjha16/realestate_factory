"""
Idempotency keys.

A generation is expensive — several model calls, a render, an upload — and the
console will retry on a dropped connection. Without a key, a double submit is two
deliverables for one instruction, two entries in the cost ledger, and two
documents a reviewer has to tell apart.

The key is SHA-256 over normalised instructions, the job type, the checksums of
every import, and the firm. The firm is in the hash deliberately: two firms
submitting byte-identical instructions are two different jobs, and collapsing
them would hand one firm's deliverable to another.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
import uuid

# Whitespace differences are not intent. A user who re-pastes the same brief with
# a trailing newline meant the same thing.
_WHITESPACE = re.compile(r"\s+")


def normalise_text(value: str) -> str:
    """
    NFKC, lowercased, whitespace collapsed.

    Deliberately conservative: it does not strip punctuation. "value at 12,00,000"
    and "value at 1200000" are different instructions and must not collapse.
    """
    folded = unicodedata.normalize("NFKC", value).strip().lower()
    return _WHITESPACE.sub(" ", folded)


def checksum_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checksum_text(value: str) -> str:
    return checksum_bytes(value.encode("utf-8"))


def build_key(
    *,
    firm_id: uuid.UUID,
    job_type: str | None,
    instructions: str,
    import_checksums: list[str] | None = None,
) -> str:
    """
    A stable 64-character key. Order of imports does not change intent, so they
    are sorted; the field separator is a NUL byte so that no combination of
    field contents can forge a different split.
    """
    parts = [
        str(firm_id),
        (job_type or "").strip().lower(),
        normalise_text(instructions),
        "|".join(sorted(import_checksums or [])),
    ]
    return hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()
