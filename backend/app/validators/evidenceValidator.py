"""
The evidence gate.

**Every assertion of legal or physical fact in a deliverable must resolve to a
record.** Ownership, tenure, encumbrance status, approvals held, area and age
each resolve to a `property_document`, a `title_chain_entry`, an `encumbrance`
row or an `approval` row. An unsupported assertion **blocks the render**.

It is never softened into hedged prose. A report that says "title appears to be
clear, subject to verification" and is then relied upon by a lender has not
disclosed anything — it has transferred the risk to a sentence nobody reads.
Blocking is the only honest outcome, which is why this gate has no bypass flag
and no `force` parameter, and why adding one would be a change to what the
product is rather than a convenience.

Two layers, because there are two ways an unsupported claim gets into a report:

  1. **Pre-flight** (`required_evidence`) — before any drafting, does this
     property carry the evidence this deliverable will need? A valuation report
     with no encumbrance certificate is blocked before a single token is spent.
  2. **Post-draft** (`scan_assertions`) — the model wrote something. Does every
     assertion of fact in it resolve? "Clear and marketable title" is blocked
     when no title chain exists, whatever the prompt said.

The patterns in `ASSERTION_RULES` are deliberately narrow. A gate that fires on
every occurrence of the word "title" would be turned off within a week, and a
gate that is off is worse than no gate because everyone believes it is on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class EvidenceClass(StrEnum):
    TITLE_CHAIN = "title_chain"
    ENCUMBRANCE_CERT = "encumbrance_certificate"
    TITLE_DEED = "title_deed"
    APPROVAL_OC = "occupancy_certificate"
    APPROVAL_CC = "commencement_certificate"
    APPROVAL_ANY = "approval"
    AREA_EVIDENCE = "area_evidence"
    TAX_RECEIPT = "tax_receipt"
    LEASE_DEED = "lease_deed"


HUMAN_NAMES = {
    EvidenceClass.TITLE_CHAIN: "a chain of title",
    EvidenceClass.ENCUMBRANCE_CERT: "an encumbrance certificate",
    EvidenceClass.TITLE_DEED: "a registered title deed",
    EvidenceClass.APPROVAL_OC: "an occupancy certificate",
    EvidenceClass.APPROVAL_CC: "a commencement certificate",
    EvidenceClass.APPROVAL_ANY: "the relevant statutory approval",
    EvidenceClass.AREA_EVIDENCE: "an approved plan or registered instrument stating the area",
    EvidenceClass.TAX_RECEIPT: "a property tax receipt",
    EvidenceClass.LEASE_DEED: "the lease deed",
}


@dataclass(frozen=True)
class EvidenceBundle:
    """
    What a property actually has. Assembled by the repository; the gate only
    reads it, so the gate itself has no database access and is trivially testable.
    """

    property_id: str
    document_kinds: frozenset[str] = frozenset()
    title_chain_length: int = 0
    title_chain_has_gap: bool = False
    encumbrance_count: int = 0
    subsisting_encumbrance_count: int = 0
    approval_kinds: frozenset[str] = frozenset()
    expired_approval_kinds: frozenset[str] = frozenset()
    # Which document each satisfied class came from, so the console can open it.
    document_ids_by_kind: dict[str, list[str]] = field(default_factory=dict)

    def has(self, evidence: EvidenceClass) -> bool:
        match evidence:
            case EvidenceClass.TITLE_CHAIN:
                return self.title_chain_length > 0 and not self.title_chain_has_gap
            case EvidenceClass.ENCUMBRANCE_CERT:
                return "encumbrance_cert" in self.document_kinds
            case EvidenceClass.TITLE_DEED:
                return "title_deed" in self.document_kinds
            case EvidenceClass.APPROVAL_OC:
                return "oc" in self.approval_kinds
            case EvidenceClass.APPROVAL_CC:
                return "cc" in self.approval_kinds
            case EvidenceClass.APPROVAL_ANY:
                return bool(self.approval_kinds)
            case EvidenceClass.AREA_EVIDENCE:
                return bool({"plan", "title_deed"} & self.document_kinds)
            case EvidenceClass.TAX_RECEIPT:
                return "tax_receipt" in self.document_kinds
            case EvidenceClass.LEASE_DEED:
                return "lease_deed" in self.document_kinds
        return False


@dataclass(frozen=True)
class MissingEvidence:
    evidence: EvidenceClass
    because: str
    quote: str | None = None

    def describe(self) -> str:
        name = HUMAN_NAMES[self.evidence]
        if self.quote:
            return f'"{self.quote}" requires {name}, and none is on record'
        return f"{self.because} requires {name}, and none is on record"


class EvidenceBlocked(Exception):
    """
    The deliverable cannot be rendered on the evidence available.

    Carries every missing item, not the first — a valuer sent away three times
    for one document at a time is a valuer who stops using the system.
    """

    def __init__(self, property_id: str, missing: list[MissingEvidence]):
        self.property_id = property_id
        self.missing = missing
        lines = "\n".join(f"  · {m.describe()}" for m in missing)
        super().__init__(
            f"blocked_evidence: {len(missing)} assertion(s) have nothing behind them.\n{lines}\n"
            f"Upload the missing records, or remove the assertions. This gate has no "
            f"bypass: an unevidenced title assertion in a signed valuation is the "
            f"claim that ends a valuer's registration."
        )


# ── layer 1: what a deliverable needs before it is drafted ───────────────────

# Keyed by job type. Each entry is what that deliverable will inevitably assert,
# so requiring it up front costs nothing and saves a full generation.
REQUIRED_BY_JOB_TYPE: dict[str, tuple[EvidenceClass, ...]] = {
    "valuation_report": (
        # A valuation states who owns it and whether anything is charged against
        # it. Both are assertions of legal fact.
        EvidenceClass.TITLE_CHAIN,
        EvidenceClass.ENCUMBRANCE_CERT,
        EvidenceClass.AREA_EVIDENCE,
    ),
    "due_diligence_report": (
        EvidenceClass.TITLE_CHAIN,
        EvidenceClass.ENCUMBRANCE_CERT,
        EvidenceClass.TITLE_DEED,
        EvidenceClass.APPROVAL_ANY,
    ),
    "construction_disbursement_report": (
        EvidenceClass.APPROVAL_CC,
        EvidenceClass.AREA_EVIDENCE,
    ),
    "sale_deed": (
        EvidenceClass.TITLE_CHAIN,
        EvidenceClass.ENCUMBRANCE_CERT,
        EvidenceClass.TITLE_DEED,
    ),
    "lease_agreement": (EvidenceClass.TITLE_DEED,),
    "rental_agreement": (EvidenceClass.TITLE_DEED,),
    "development_agreement": (EvidenceClass.TITLE_CHAIN, EvidenceClass.TITLE_DEED),
    "power_of_attorney": (EvidenceClass.TITLE_DEED,),
}

WHY_REQUIRED = {
    EvidenceClass.TITLE_CHAIN: "a report that states who owns the property",
    EvidenceClass.ENCUMBRANCE_CERT: "a report that states whether the property is charged",
    EvidenceClass.TITLE_DEED: "an instrument that transfers or grants an interest",
    EvidenceClass.AREA_EVIDENCE: "a figure computed from the property's area",
    EvidenceClass.APPROVAL_ANY: "a report that lists the approvals held",
    EvidenceClass.APPROVAL_CC: "a disbursement certified against construction stages",
    EvidenceClass.APPROVAL_OC: "a statement that the building may be occupied",
    EvidenceClass.TAX_RECEIPT: "a statement about rates and taxes",
    EvidenceClass.LEASE_DEED: "a statement about the terms of a tenancy",
}


def required_evidence(job_type: str) -> tuple[EvidenceClass, ...]:
    return REQUIRED_BY_JOB_TYPE.get(job_type, ())


def check_preflight(bundle: EvidenceBundle, job_type: str) -> list[MissingEvidence]:
    """Before a token is spent. Returns what is missing; the caller blocks."""
    return [
        MissingEvidence(evidence=required, because=WHY_REQUIRED[required])
        for required in required_evidence(job_type)
        if not bundle.has(required)
    ]


# ── layer 2: what the model actually wrote ───────────────────────────────────


@dataclass(frozen=True)
class AssertionRule:
    """A phrase that asserts a fact, and the record class that supports it."""

    pattern: re.Pattern[str]
    evidence: EvidenceClass
    description: str


def _rule(regex: str, evidence: EvidenceClass, description: str) -> AssertionRule:
    return AssertionRule(re.compile(regex, re.IGNORECASE), evidence, description)


# Narrow on purpose. Each of these is an unqualified statement of fact that a
# reader will rely on, not a description of methodology or a caveat.
ASSERTION_RULES: tuple[AssertionRule, ...] = (
    _rule(
        r"\b(clear|clean)\s+and\s+marketable\s+title\b",
        EvidenceClass.TITLE_CHAIN,
        "an assertion that title is clear and marketable",
    ),
    _rule(
        r"\bmarketable\s+title\b",
        EvidenceClass.TITLE_CHAIN,
        "an assertion that title is marketable",
    ),
    _rule(
        r"\btitle\s+is\s+(clear|good|valid|absolute|unencumbered)\b",
        EvidenceClass.TITLE_CHAIN,
        "an assertion about the quality of title",
    ),
    _rule(
        r"\b(free\s+from|free\s+of|not\s+subject\s+to)\s+(all\s+)?"
        r"(encumbrance|encumbrances|charge|charges|lien|liens|mortgage)\b",
        EvidenceClass.ENCUMBRANCE_CERT,
        "an assertion that the property is unencumbered",
    ),
    _rule(
        # "no encumbrance subsists" asserts a fact about the property.
        # "no encumbrance search was undertaken" discloses a limit on the work.
        # The lookahead is what tells them apart, and getting this wrong in the
        # permissive direction is how a gate ends up switched off.
        r"\bno\s+(subsisting\s+)?(encumbrance|encumbrances|charge|charges|lien|liens)\b"
        r"(?!\s+(search|certificate|report|investigation|enquiry|inquiry|has\s+been\s+"
        r"(undertaken|carried|obtained)))",
        EvidenceClass.ENCUMBRANCE_CERT,
        "an assertion that no encumbrance subsists",
    ),
    _rule(
        r"\b(is|are)\s+the\s+(absolute|lawful|rightful)\s+owner",
        EvidenceClass.TITLE_CHAIN,
        "an assertion of ownership",
    ),
    _rule(
        r"\b(seized\s+and\s+possessed|absolutely\s+seized)\b",
        EvidenceClass.TITLE_CHAIN,
        "an assertion of seisin",
    ),
    _rule(
        r"\boccupancy\s+certificate\s+(has\s+been\s+)?(obtained|issued|granted)\b",
        EvidenceClass.APPROVAL_OC,
        "an assertion that an occupancy certificate has been obtained",
    ),
    _rule(
        r"\bcommencement\s+certificate\s+(has\s+been\s+)?(obtained|issued|granted)\b",
        EvidenceClass.APPROVAL_CC,
        "an assertion that a commencement certificate has been obtained",
    ),
    _rule(
        r"\ball\s+(statutory\s+)?approvals?\s+(are\s+)?(in\s+place|obtained|held)\b",
        EvidenceClass.APPROVAL_ANY,
        "an assertion that the statutory approvals are held",
    ),
    _rule(
        r"\b(municipal|property)\s+tax(es)?\s+(have\s+been\s+|are\s+)?(paid|cleared|up\s+to\s+date)\b",
        EvidenceClass.TAX_RECEIPT,
        "an assertion that rates and taxes are paid",
    ),
    _rule(
        r"\btenure\s+is\s+(freehold|leasehold)\b",
        EvidenceClass.TITLE_DEED,
        "an assertion about tenure",
    ),
)


def scan_assertions(text: str, bundle: EvidenceBundle) -> list[MissingEvidence]:
    """
    Every assertion in the text that has nothing behind it.

    Case-insensitive and quote-preserving: the block message shows the sentence
    the valuer has to deal with, not a rule name.
    """
    missing: list[MissingEvidence] = []
    seen: set[tuple[EvidenceClass, str]] = set()

    for rule in ASSERTION_RULES:
        for match in rule.pattern.finditer(text or ""):
            if bundle.has(rule.evidence):
                continue
            quote = _sentence_around(text, match.start(), match.end())
            key = (rule.evidence, quote)
            if key in seen:
                continue
            seen.add(key)
            missing.append(
                MissingEvidence(evidence=rule.evidence, because=rule.description, quote=quote)
            )
    return missing


def _sentence_around(text: str, start: int, end: int, width: int = 160) -> str:
    left = max(text.rfind(".", 0, start), text.rfind("\n", 0, start)) + 1
    right = min(
        (i for i in (text.find(".", end), text.find("\n", end)) if i != -1),
        default=len(text),
    )
    sentence = text[left : right + 1].strip()
    return sentence[:width] + ("…" if len(sentence) > width else "")


# ── the gate ─────────────────────────────────────────────────────────────────


def enforce(
    bundle: EvidenceBundle,
    *,
    job_type: str,
    drafted_text: str | None = None,
    as_of: date | None = None,
) -> None:
    """
    Raise `EvidenceBlocked` if anything is unsupported.

    There is no `force`, no `allow_missing`, and no severity threshold. Adding
    one would change what this product is: the whole professional-liability
    posture rests on a report never asserting a fact it cannot show.
    """
    missing = check_preflight(bundle, job_type)
    if drafted_text:
        missing += scan_assertions(drafted_text, bundle)

    if missing:
        raise EvidenceBlocked(bundle.property_id, missing)
