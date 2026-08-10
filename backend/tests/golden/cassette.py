"""
LLM cassette — record / replay for the golden set.

The golden set exists to prove that S1's restructuring changed no behaviour.
That proof is only worth something if the run is reproducible, and a live LLM
call is not. So every LLM call in a golden run goes through this cassette:

  replay      (default) — look the call up by hash; a miss is a hard error.
  synthesise  — a miss is filled by a canned, deterministic response and
                written back to the cassette. This is how the cassettes in
                this directory were authored without provider keys.
  record      — a miss calls the real provider and writes the response back.
                `make golden-record` uses this once GROQ_API_KEY is set.

The hash covers model, messages, max_tokens and json_mode, so any prompt change
misses the cassette and is caught rather than silently replayed.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

MODES = ("replay", "synthesise", "record")


def call_key(model: str, messages: list, max_tokens: int, json_mode: bool) -> str:
    payload = json.dumps(
        {"model": model, "messages": messages, "max_tokens": max_tokens, "json_mode": json_mode},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


class Cassette:
    def __init__(self, path: Path, mode: str = "replay", job_types: set | None = None):
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
        self.path = Path(path)
        self.mode = mode
        self.job_types = job_types or set()
        self.entries: dict = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.dirty = False
        self.calls: list[str] = []

    # ── the callable that replaces `_chat` in the graph module ────────────────

    def chat(self, messages: list, max_tokens: int = 4096, json_mode: bool = False) -> str:
        model = os.environ.get("ROUTER_MODEL", "llama-3.3-70b-versatile")
        key = call_key(model, messages, max_tokens, json_mode)
        self.calls.append(key)

        if key in self.entries:
            return self.entries[key]["response"]

        if self.mode == "replay":
            system = _first(messages, "system")[:120]
            raise KeyError(
                f"cassette miss in {self.path.name} for key {key}\n"
                f"  system prompt: {system!r}\n"
                f"  A miss means the prompt or its inputs changed. Re-record with "
                f"`make golden-record` if the change is intended."
            )

        response = (
            _synthesise(messages, self.job_types)
            if self.mode == "synthesise"
            else _live(model, messages, max_tokens, json_mode)
        )
        self.entries[key] = {
            "system_excerpt": _first(messages, "system")[:200],
            "response": response,
        }
        self.dirty = True
        return response

    def save(self) -> None:
        if self.dirty:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.entries, indent=2, ensure_ascii=False) + "\n")
            self.dirty = False


def _first(messages: list, role: str) -> str:
    for m in messages:
        if m.get("role") == role:
            return m.get("content", "")
    return ""


def _live(model: str, messages: list, max_tokens: int, json_mode: bool) -> str:
    from groq import Groq

    kwargs = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": float(os.environ.get("LLM_TEMPERATURE", "0.2")),
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = Groq(api_key=os.environ["GROQ_API_KEY"]).chat.completions.create(**kwargs)
    return resp.choices[0].message.content.strip()


# ── canned responses ──────────────────────────────────────────────────────────
#
# Deterministic stand-ins, shaped exactly like what each node parses. They carry
# no figures: under S1 the model is already forbidden from originating a number,
# and a cassette that invented one would let a figure regression pass unnoticed.

_STRUCTURES = {
    "valuation_report": [
        ("Executive Summary", "executive_summary"),
        ("Property Description", "property_description"),
        ("Location Analysis", "market_analysis"),
        ("Market Analysis", "market_analysis"),
        ("Sales Comparison Approach", "valuation_approach"),
        ("Income Approach", "valuation_approach"),
        ("Cost Approach", "valuation_approach"),
        ("Reconciliation of Value", "valuation_approach"),
        ("Conclusion & Certificate", "conclusion"),
    ],
    "due_diligence_report": [
        ("Executive Summary", "executive_summary"),
        ("Property Description", "property_description"),
        ("Title Chain Analysis", "due_diligence_check"),
        ("Encumbrance Review", "due_diligence_check"),
        ("Approvals & Permissions", "due_diligence_check"),
        ("Litigation Search", "due_diligence_check"),
        ("Zoning & Land Use", "due_diligence_check"),
        ("Risk Summary", "recommendations"),
        ("Recommendations", "recommendations"),
    ],
    "construction_disbursement_report": [
        ("Executive Summary", "executive_summary"),
        ("Project Overview", "property_description"),
        ("Stage-wise Progress", "construction_stage"),
        ("Disbursement Eligibility", "construction_stage"),
        ("Outstanding Tranches", "construction_stage"),
        ("Recommendations", "recommendations"),
    ],
}

_COMPLIANCE_SECTIONS = {
    "rera_quarterly_report": [
        ("Project Registration Particulars", "s.11(1)"),
        ("Quarterly Progress of Development Works", "s.11(1)(a)"),
        ("Status of Booked and Unbooked Inventory", "s.11(1)(b)"),
        ("Statutory Approvals Obtained During the Quarter", "s.11(1)(c)"),
        ("Designated Account Position", "s.4(2)(l)(D)"),
        ("Declaration by the Promoter", "s.4(2)(l)"),
    ],
    "rera_registration": [
        ("Promoter Particulars", "s.4(2)(a)"),
        ("Project Particulars", "s.4(2)(b)"),
        ("Sanctioned Plan and Approvals", "s.4(2)(c)"),
        ("Declaration and Undertaking", "s.4(2)(l)"),
    ],
}

_AGREEMENT_CLAUSES = {
    "lease_agreement": [
        "Parties", "Recitals", "Demised Premises", "Term and Lock-in",
        "Rent and Escalation", "Security Deposit", "Lessor's Covenants",
        "Lessee's Covenants", "Termination", "Stamp Duty and Registration",
        "Execution",
    ],
    "sale_deed": [
        "Parties", "Recitals", "Consideration", "Schedule of Property",
        "Representations and Warranties", "Covenants for Title",
        "Delivery of Possession", "Stamp Duty and Registration", "Execution",
    ],
}
_AGREEMENT_DEFAULT = [
    "Parties", "Recitals", "Subject Matter", "Consideration",
    "Representations", "Covenants", "Termination",
    "Stamp Duty and Registration", "Execution",
]


def _synthesise(messages: list, job_types: set) -> str:
    system = _first(messages, "system")
    user = _first(messages, "user")

    if "intake agent" in system:
        return json.dumps({
            "doc_type": _detect_job_type(user, job_types),
            "client_name": _grab(user, r"[Cc]lient[:\s]+([A-Za-z0-9 .&'-]+)") or "Client",
            "property_address": _grab(user, r"[Pp]roperty[:\s]+([^\n.]+)") or "",
            "property_type": _grab(user, r"property type[:\s]+([A-Za-z ]+)") or "",
            "purpose": _grab(user, r"[Pp]urpose[:\s]+([^\n.]+)") or "",
            "special_notes": "",
        })

    if "senior real estate consultant" in system:
        return (
            "Applicable framework: the Real Estate (Regulation and Development) Act 2016, "
            "the Transfer of Property Act 1882, the Registration Act 1908 and the relevant "
            "State Stamp Act govern the instrument and its registration.\n\n"
            "Market context: the locality is assessed on the evidence placed on record. No "
            "market figure is stated here; every figure in the deliverable is computed and "
            "carried through from the valuation lines.\n\n"
            "Methodology: the sales comparison, income capitalisation and cost approaches are "
            "each considered, and the conclusion is reconciled with a stated rationale per weight.\n\n"
            "Due diligence: title chain, encumbrance certificate, mutation records, approved "
            "plans, commencement and occupancy certificates and tax receipts are to be inspected."
        )

    if "report architect" in system:
        doc_type = _grab(user, r"Document:\s*([a-z_]+)") or "valuation_report"
        sections = _STRUCTURES.get(doc_type, _STRUCTURES["valuation_report"])
        return json.dumps({
            "title": doc_type.replace("_", " ").title(),
            "sections": [
                {"heading": h, "type": t, "notes": f"Address {h.lower()} on the evidence of record."}
                for h, t in sections
            ],
        })

    if "compliance document architect" in system:
        doc_type = _grab(user, r"Document:\s*([a-z_]+)") or "rera_registration"
        sections = _COMPLIANCE_SECTIONS.get(doc_type) or _COMPLIANCE_SECTIONS["rera_registration"]
        return json.dumps({
            "title": doc_type.replace("_", " ").title(),
            "sections": [
                {"heading": h, "clause_ref": ref, "notes": f"Mandatory disclosure under {ref}."}
                for h, ref in sections
            ],
        })

    if "registered valuer (IBBI)" in system:
        return json.dumps({"approved": True, "feedback": "Methodology and approach coverage are adequate."})
    if "property buyer/bank" in system:
        return json.dumps({"approved": True, "feedback": "Conclusion and risk summary are locatable."})
    if "RERA authority officer" in system:
        return json.dumps({"approved": True, "feedback": "Mandatory disclosures are present."})
    if "real estate developer reviewing" in system:
        return json.dumps({"approved": True, "feedback": "No section is missing that would cause rejection."})

    if "real estate document writer" in system:
        heading = _grab(user, r"Section:\s*(.+)") or "Section"
        sec_type = _grab(user, r"Type:\s*(\S+)") or "standard_clause"
        return json.dumps({
            "heading": heading,
            "content": (
                f"This section sets out the {heading.lower()} for the subject property. "
                "The analysis rests on the documents and data placed on record and is to be "
                "read with the assumptions and limiting conditions. Figures stated elsewhere in "
                "this report are computed from the schedules annexed and are not restated here."
            ),
            "type": sec_type,
        })

    if "compliance document writer" in system:
        headings = re.findall(r'"heading":\s*"([^"]+)"', user)
        refs = re.findall(r'"clause_ref":\s*"([^"]+)"', user)
        return json.dumps([
            {
                "heading": h,
                "type": "standard_clause",
                "clause_ref": refs[i] if i < len(refs) else "",
                "content": (
                    f"{h}: the particulars required under this head are furnished from the "
                    "project records maintained by the promoter and are true to the best of "
                    "the promoter's knowledge."
                ),
            }
            for i, h in enumerate(headings)
        ])

    if "legal document drafter" in system:
        doc_type = _grab(user, r"Document:\s*([a-z_]+)") or "sale_deed"
        return json.dumps([
            {
                "heading": h,
                "type": "numbered_clause",
                "content": (
                    f"{h}: this clause is drafted in accordance with the Transfer of Property "
                    "Act 1882, the Registration Act 1908 and the applicable State Stamp Act, "
                    "and takes effect on execution and registration of this instrument."
                ),
            }
            for h in _AGREEMENT_CLAUSES.get(doc_type, _AGREEMENT_DEFAULT)
        ])

    if "document repair agent" in system:
        return json.dumps([{"heading": "Document", "type": "standard_clause",
                            "content": "Repaired clause plan."}])

    raise KeyError(f"no canned response for system prompt: {system[:160]!r}")


def _detect_job_type(text: str, job_types: set) -> str:
    lowered = text.lower()
    for jt in sorted(job_types, key=len, reverse=True):
        if jt in lowered or jt.replace("_", " ") in lowered:
            return jt
    return "valuation_report"


def _grab(text: str, pattern: str) -> str:
    m = re.search(pattern, text)
    return m.group(1).strip() if m else ""
