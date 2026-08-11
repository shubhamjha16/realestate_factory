"""
RE Graph — Real Estate Factory
14-node LangGraph pipeline with 4 paths:
  Valuation path      — section_drafter loop (valuation report, due diligence, construction)
  Compliance path     — structure → critic → drafter (RERA, FEMA, NOC, EIA)
  Agreement path      — single-shot drafter (sale deed, lease, MOU)
  Reconciliation path — deterministic zero-LLM (rent roll, portfolio report)
"""

import json
from decimal import Decimal
from typing import TypedDict, Optional, List
from langgraph.graph import StateGraph, END
from groq import Groq

from app.configs import jobTypes as config
from app.configs.envConfig import settings
from app.services.graph.nodes.evidenceCheck import evidence_check_node, evidence_route
from app.services.ingest.propertyDataParser import parse_property_data
from app.services.ingest.result import MalformedInputError, UnrecognisedFormatError
from app.services.valuation.money import format_inr, try_decimal
from app.services.valuation.valuationCalculator import compute as val_compute

# ── LLM client ────────────────────────────────────────────────────────────────

_groq = Groq(api_key=settings.GROQ_API_KEY)
MODEL = settings.ROUTER_MODEL

def _chat(messages: list, max_tokens: int = 4096, json_mode: bool = False) -> str:
    kwargs = {"model": MODEL, "messages": messages, "max_tokens": max_tokens,
              "temperature": settings.LLM_TEMPERATURE}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = _groq.chat.completions.create(**kwargs)
    return resp.choices[0].message.content.strip()


# ── State ──────────────────────────────────────────────────────────────────────

class REState(TypedDict):
    # Input
    raw_instructions:   str
    raw_property_data:  str
    job_type:           Optional[str]
    _job_id:            str

    # Parsed intake
    doc_type:           Optional[str]
    client_name:        Optional[str]
    property_address:   Optional[str]
    property_type:      Optional[str]
    purpose:            Optional[str]
    special_notes:      Optional[str]

    # Property data
    parsed_data:        Optional[dict]
    computed:           Optional[dict]

    # Tenancy and subject, for the evidence gate (S8)
    property_id:        Optional[str]
    _scope:             Optional[object]

    # Evidence gate
    evidence_checked:   bool
    evidence_bundle:    Optional[dict]
    evidence_missing:   Optional[List[str]]
    _blocked:           bool

    # Research
    re_research:        Optional[str]

    # Vision (letterhead)
    header_image_path:  Optional[str]

    # Structure / critic loop
    structure_plan:     Optional[dict]
    structure_attempt:  int
    critic_feedback:    Optional[str]
    _critic_approved:   bool

    # Section drafter loop
    section_index:      int
    drafted_sections:   Optional[List[dict]]

    # Renderer
    clause_plan:        Optional[List[dict]]
    render_attempt:     int
    render_error:       Optional[str]

    # Output
    doc_path:           Optional[str]
    doc_url:            Optional[str]
    generation_errors:  Optional[str]


def _safe(state, key, default=None):
    return state.get(key) or default


# ══════════════════════════════════════════════════════════════════════════════
# NODE 1 — intake_node
# ══════════════════════════════════════════════════════════════════════════════

def intake_node(state: REState) -> dict:
    system = (
        "You are a real estate document intake agent. "
        "Extract metadata from the instructions and return a JSON object with keys: "
        "doc_type, client_name, property_address, property_type, purpose, special_notes. "
        f"doc_type must be one of: {', '.join(config.ALL_JOB_TYPES)}. "
        "Return JSON only."
    )
    raw = _chat([{"role": "system", "content": system},
                 {"role": "user",   "content": state["raw_instructions"]}], json_mode=True)
    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = {}

    doc_type = parsed.get("doc_type") or state.get("job_type") or "valuation_report"
    return {
        "doc_type":        doc_type,
        "client_name":     parsed.get("client_name"),
        "property_address": parsed.get("property_address"),
        "property_type":   parsed.get("property_type"),
        "purpose":         parsed.get("purpose"),
        "special_notes":   parsed.get("special_notes"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# NODE 2 — property_data_parser_node
# ══════════════════════════════════════════════════════════════════════════════

_EMPTY_PARSE = {
    "format": "empty", "records": [], "rejected": [],
    "counts": {"input": 0, "parsed": 0, "rejected": 0, "duplicate": 0},
    "metadata": {},
}


def property_data_parser_node(state: REState) -> dict:
    raw = _safe(state, "raw_property_data", "")
    if not raw:
        return {"parsed_data": dict(_EMPTY_PARSE)}

    # S6: an unrecognised or malformed payload is an error, not an empty
    # structure. It is surfaced on the state so the job fails with a reason a
    # valuer can act on, rather than rendering a report over nothing.
    try:
        result = parse_property_data(raw)
    except (UnrecognisedFormatError, MalformedInputError) as e:
        unparseable = {**_EMPTY_PARSE, "format": "unparseable", "metadata": {"error": str(e)}}
        return {
            "parsed_data": unparseable,
            "generation_errors": f"property data could not be parsed: {e}",
        }

    return {"parsed_data": result.to_dict()}


# ══════════════════════════════════════════════════════════════════════════════
# NODE 3 — valuation_calculator_node
# ══════════════════════════════════════════════════════════════════════════════

def valuation_calculator_node(state: REState) -> dict:
    parsed   = _safe(state, "parsed_data", {})
    doc_type = _safe(state, "doc_type", "")
    if not parsed or not parsed.get("records"):
        return {"computed": {"type": "empty"}}
    try:
        computed = val_compute(parsed, doc_type)
    except ValueError as e:
        return {"computed": {"type": "error", "error": str(e)}, "generation_errors": str(e)}
    return {"computed": computed}


# ══════════════════════════════════════════════════════════════════════════════
# NODE 4 — research_node
# ══════════════════════════════════════════════════════════════════════════════

def research_node(state: REState) -> dict:
    doc_type = _safe(state, "doc_type", "valuation_report")
    prop     = _safe(state, "property_address", "the subject property")
    computed = _safe(state, "computed", {})

    system = "You are a senior real estate consultant. Provide concise reference guidance for drafting the document. 3-4 paragraphs max."
    user   = (
        f"Document type: {doc_type}\nProperty: {prop}\n"
        f"Computed data summary: {json.dumps({k: v for k, v in computed.items() if k != 'unit_details' and k != 'stage_details' and k != 'properties'}, indent=2, default=str)}\n"
        "Provide: applicable regulations (RERA, Transfer of Property Act, Registration Act, Stamp Duty), "
        "market context, standard methodologies (Sales Comparison, Income, Cost approach), "
        "due diligence checklist items, and key clauses for the document type."
    )
    research = _chat([{"role": "system", "content": system}, {"role": "user", "content": user}])
    return {"re_research": research}


# ══════════════════════════════════════════════════════════════════════════════
# NODE 5 — vision_node
# ══════════════════════════════════════════════════════════════════════════════

def vision_node(state: REState) -> dict:
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model  = genai.ImageGenerationModel("imagen-3.0-generate-002")
        client = _safe(state, "client_name", "RealEstate")
        result = model.generate_images(
            prompt=f"Professional real estate valuation report letterhead for {client}, "
                   "navy blue and gold, property icon, clean corporate style, white background",
            number_of_images=1, aspect_ratio="16:1",
        )
        img_path = f"/tmp/{state['_job_id']}_header.png"
        result.images[0].save(img_path)
        return {"header_image_path": img_path}
    except Exception:
        return {"header_image_path": None}


# ══════════════════════════════════════════════════════════════════════════════
# ROUTING after vision
# ══════════════════════════════════════════════════════════════════════════════

def _gated_route(state: REState) -> str:
    """
    The evidence gate and the path choice, in one decision.

    Combined deliberately: two routers off the same node could disagree, and the
    disagreement would be a path around the gate.
    """
    if evidence_route(state) == "blocked":
        return "blocked"
    return _vision_route(state)


def _vision_route(state: REState) -> str:
    doc_type = _safe(state, "doc_type", "")
    if doc_type in config.RECONCILIATION_TYPES:
        return "rec_renderer"
    if doc_type in config.VALUATION_TYPES:
        return "valuation_structure"
    if doc_type in config.COMPLIANCE_TYPES:
        return "compliance_structure"
    return "agreement_drafter"


# ══════════════════════════════════════════════════════════════════════════════
# RECONCILIATION PATH — zero LLM
# ══════════════════════════════════════════════════════════════════════════════

def _money(computed: dict, key: str) -> str:
    """A computed figure, in rupees with Indian grouping. Never re-derived here."""
    return format_inr(try_decimal(computed.get(key, "0"), Decimal(0)))


def _num(record: dict, key: str) -> str:
    value = try_decimal(record.get(key, "0"), Decimal(0))
    return format_inr(value)


def rec_renderer_node(state: REState) -> dict:
    """Format computed rent roll / portfolio dict directly into clause_plan. No LLM."""
    computed = _safe(state, "computed", {})
    doc_type = _safe(state, "doc_type", "rent_roll_report")
    client   = _safe(state, "client_name", "Client")
    prop     = _safe(state, "property_address", "")
    clauses  = []

    if computed.get("type") == "rent_roll":
        clauses = [
            {"heading": "Rent Roll Summary", "type": "summary_table", "content":
                f"Property: {prop}\nClient: {client}\n"
                f"Total Units: {computed.get('total_units',0)} | "
                f"Occupied: {computed.get('occupied_units',0)} | "
                f"Vacant: {computed.get('vacant_units',0)}\n"
                f"Vacancy Rate: {computed.get('vacancy_rate_pct',0)}%\n"
                f"Total Monthly Rent: {_money(computed, 'total_monthly_rent')}\n"
                f"Total Annual Rent: {_money(computed, 'total_annual_rent')}\n"
                f"Total Security Deposit: {_money(computed, 'total_security_deposit')}\n"
                f"Total Overdue: {_money(computed, 'total_overdue')}"},
            {"heading": "Unit-wise Details", "type": "unit_table",
             "content": _format_units(computed.get("unit_details", []))},
            {"heading": "Upcoming Escalations", "type": "standard_clause",
             "content": _format_escalations(computed.get("upcoming_escalations", []))},
        ]
    elif computed.get("type") == "portfolio":
        clauses = [
            {"heading": "Portfolio Summary", "type": "summary_table", "content":
                f"Client: {client}\n"
                f"Total Properties: {computed.get('total_properties',0)}\n"
                f"Total Portfolio Value: {_money(computed, 'total_portfolio_value')}\n"
                f"Total Cost: {_money(computed, 'total_cost')}\n"
                f"Total Equity: {_money(computed, 'total_equity')}\n"
                f"Loan Outstanding: {_money(computed, 'total_loan_outstanding')}\n"
                f"Annual Rental Income: {_money(computed, 'annual_rental_income')}\n"
                f"Portfolio Yield: {computed.get('portfolio_yield_pct',0)}%\n"
                f"Appreciation: {computed.get('appreciation_pct',0)}%"},
            {"heading": "Property-wise Breakdown", "type": "unit_table",
             "content": _format_portfolio(computed.get("properties", []))},
        ]
    else:
        clauses = [{"heading": "Report", "type": "standard_clause",
                    "content": json.dumps(computed, indent=2, default=str)}]

    return {"clause_plan": clauses}


def _format_units(units):
    if not units:
        return "No units found."
    lines = ["Unit | Tenant | Area | Monthly Rent | Status | Overdue"]
    for u in units:
        lines.append(
            f"{u.get('unit','')} | {u.get('tenant','')} | "
            f"{u.get('area_sqft',0)} sqft | {_num(u, 'monthly_rent')} | "
            f"{u.get('status','')} | {_num(u, 'overdue')}"
        )
    return "\n".join(lines)


def _format_escalations(esc):
    if not esc:
        return "No upcoming escalations."
    lines = ["Unit | Tenant | Current Rent | New Rent | Escalation%"]
    for e in esc:
        lines.append(
            f"{e.get('unit','')} | {e.get('tenant','')} | "
            f"{_num(e, 'current_rent')} | {_num(e, 'new_rent')} | "
            f"{e.get('escalation_pct',0)}%"
        )
    return "\n".join(lines)


def _format_portfolio(props):
    if not props:
        return "No properties found."
    lines = ["Property | Type | Area | Value | Monthly Rent | Loan"]
    for p in props:
        lines.append(
            f"{p.get('property_name','')} | {p.get('property_type','')} | "
            f"{p.get('area_sqft',0)} sqft | {_num(p, 'current_value')} | "
            f"{_num(p, 'monthly_rent')} | {_num(p, 'loan_outstanding')}"
        )
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# VALUATION PATH
# ══════════════════════════════════════════════════════════════════════════════

def valuation_structure_node(state: REState) -> dict:
    doc_type  = _safe(state, "doc_type", "valuation_report")
    prop      = _safe(state, "property_address", "")
    client    = _safe(state, "client_name", "")
    computed  = _safe(state, "computed", {})
    research  = _safe(state, "re_research", "")

    system = (
        "You are a real estate report architect. "
        "Build a structured report outline as a JSON object. Return JSON only."
    )
    user = (
        f"Document: {doc_type}\nClient: {client}\nProperty: {prop}\n"
        f"Computed data: {json.dumps({k: v for k, v in computed.items() if 'detail' not in k and 'properties' not in k}, indent=2, default=str)}\n"
        f"Research:\n{research}\n\n"
        "Return: {\"title\": str, \"sections\": [{\"heading\": str, \"type\": str, \"notes\": str}]} "
        "For valuation_report include: Executive Summary, Property Description, "
        "Location Analysis, Market Analysis, Sales Comparison Approach, "
        "Income Approach, Cost Approach, Reconciliation of Value, Conclusion & Certificate. "
        "For due_diligence_report include: Executive Summary, Property Description, "
        "Title Chain Analysis, Encumbrance Review, Approvals & Permissions, "
        "Litigation Search, Zoning & Land Use, Risk Summary, Recommendations. "
        "For construction_disbursement_report include: Executive Summary, Project Overview, "
        "Stage-wise Progress, Disbursement Eligibility, Outstanding Tranches, Recommendations. "
        "section type: executive_summary, property_description, market_analysis, "
        "valuation_approach, due_diligence_check, construction_stage, recommendations, conclusion."
    )
    raw = _chat([{"role": "system", "content": system}, {"role": "user", "content": user}],
                max_tokens=2500, json_mode=True)
    try:
        plan = json.loads(raw)
    except Exception:
        plan = {"title": doc_type.replace("_", " ").title(), "sections": []}

    return {
        "structure_plan":    plan,
        "structure_attempt": state.get("structure_attempt", 0) + 1,
        "drafted_sections":  [],
        "section_index":     0,
    }


def valuation_critic_node(state: REState) -> dict:
    plan     = _safe(state, "structure_plan", {})
    research = _safe(state, "re_research", "")

    _SOUL_VALUER = (
        "You are a registered valuer (IBBI) reviewing a real estate report structure. "
        "Check: correct valuation methodology, adequate market evidence, "
        "regulatory compliance (RERA, Companies Act for valuations), completeness. "
        "Return JSON only with keys: approved (bool), feedback (str)."
    )
    _SOUL_CLIENT = (
        "You are a property buyer/bank reviewing the report structure for clarity and usability. "
        "Check: clear conclusion, actionable risk summary, easy navigation, "
        "sufficient supporting data. "
        "Return JSON only with keys: approved (bool), feedback (str)."
    )

    def _review(soul):
        raw = _chat([{"role": "system", "content": soul},
                     {"role": "user",   "content": f"Plan:\n{json.dumps(plan, indent=2, default=str)}\n\nContext:\n{research}"}],
                    max_tokens=600, json_mode=True)
        try:
            return json.loads(raw)
        except Exception:
            return {"approved": True, "feedback": ""}

    r1 = _review(_SOUL_VALUER)
    r2 = _review(_SOUL_CLIENT)
    approved = r1.get("approved", True) and r2.get("approved", True)
    feedback = f"Valuer: {r1.get('feedback','')} | Client: {r2.get('feedback','')}"
    return {"_critic_approved": approved, "critic_feedback": feedback}


def _valuation_critic_route(state: REState) -> str:
    if state.get("_critic_approved"):
        return "section_drafter"
    if state.get("structure_attempt", 0) >= settings.MAX_CRITIC_RETRIES:
        return "section_drafter"
    return "valuation_structure"


def section_drafter_node(state: REState) -> dict:
    plan     = _safe(state, "structure_plan", {})
    sections = plan.get("sections", [])
    idx      = state.get("section_index", 0)
    drafted  = list(state.get("drafted_sections") or [])
    computed = _safe(state, "computed", {})

    if idx >= len(sections):
        return {"clause_plan": drafted, "section_index": idx}

    sec      = sections[idx]
    heading  = sec.get("heading", f"Section {idx+1}")
    sec_type = sec.get("type", "standard_clause")
    notes    = sec.get("notes", "")

    # Attach computed data for relevant sections
    data_ctx = ""
    if sec_type in ("valuation_approach", "market_analysis"):
        data_ctx = f"Computed data:\n{json.dumps({k: v for k, v in computed.items() if 'detail' not in k and 'properties' not in k}, indent=2, default=str)}\n"

    system = (
        "You are a real estate document writer. "
        "Draft this section in professional language. "
        "Return JSON only with keys: heading (str), content (str), type (str)."
    )
    user = (
        f"Section: {heading}\nType: {sec_type}\nNotes: {notes}\n{data_ctx}"
        f"Property: {_safe(state,'property_address','')}\n"
        f"Client: {_safe(state,'client_name','')}\n"
        f"Research:\n{_safe(state,'re_research','')[:1000]}\n\n"
        "Draft the full section. For valuation sections include specific figures, "
        "methodology explanation, and conclusions. Return JSON."
    )
    raw = _chat([{"role": "system", "content": system}, {"role": "user", "content": user}],
                max_tokens=2000, json_mode=True)
    try:
        section_obj = json.loads(raw)
    except Exception:
        section_obj = {"heading": heading, "content": raw, "type": sec_type}

    drafted.append(section_obj)
    return {"drafted_sections": drafted, "section_index": idx + 1, "clause_plan": drafted}


def _section_drafter_route(state: REState) -> str:
    plan     = _safe(state, "structure_plan", {})
    sections = plan.get("sections", [])
    idx      = state.get("section_index", 0)
    return "section_drafter" if idx < len(sections) else "renderer"


# ══════════════════════════════════════════════════════════════════════════════
# COMPLIANCE PATH
# ══════════════════════════════════════════════════════════════════════════════

def compliance_structure_node(state: REState) -> dict:
    doc_type = _safe(state, "doc_type", "rera_registration")
    client   = _safe(state, "client_name", "")
    prop     = _safe(state, "property_address", "")
    research = _safe(state, "re_research", "")

    system = (
        "You are a real estate compliance document architect. "
        "Build a compliance document structure as JSON. Return JSON only."
    )
    user = (
        f"Document: {doc_type}\nClient: {client}\nProperty: {prop}\n"
        f"Research:\n{research}\n\n"
        "Return: {\"title\": str, \"sections\": [{\"heading\": str, \"clause_ref\": str, \"notes\": str}]} "
        "Cover all mandatory sections for the document type as per Indian regulations."
    )
    raw = _chat([{"role": "system", "content": system}, {"role": "user", "content": user}],
                max_tokens=2000, json_mode=True)
    try:
        plan = json.loads(raw)
    except Exception:
        plan = {"title": doc_type.replace("_", " ").title(), "sections": []}

    return {"structure_plan": plan, "structure_attempt": state.get("structure_attempt", 0) + 1}


def compliance_critic_node(state: REState) -> dict:
    plan     = _safe(state, "structure_plan", {})
    research = _safe(state, "re_research", "")

    _SOUL_REGULATOR = (
        "You are a RERA authority officer reviewing a compliance document structure. "
        "Check: all mandatory disclosures present, correct regulatory references, "
        "proper format as per regulations. "
        "Return JSON only with keys: approved (bool), feedback (str)."
    )
    _SOUL_DEVELOPER = (
        "You are a real estate developer reviewing the compliance document structure. "
        "Check: practical completeness, no missing sections that could cause rejection, "
        "clear and actionable content. "
        "Return JSON only with keys: approved (bool), feedback (str)."
    )

    def _review(soul):
        raw = _chat([{"role": "system", "content": soul},
                     {"role": "user",   "content": f"Plan:\n{json.dumps(plan, indent=2, default=str)}\n\nContext:\n{research}"}],
                    max_tokens=600, json_mode=True)
        try:
            return json.loads(raw)
        except Exception:
            return {"approved": True, "feedback": ""}

    r1 = _review(_SOUL_REGULATOR)
    r2 = _review(_SOUL_DEVELOPER)
    approved = r1.get("approved", True) and r2.get("approved", True)
    feedback = f"Regulator: {r1.get('feedback','')} | Developer: {r2.get('feedback','')}"
    return {"_critic_approved": approved, "critic_feedback": feedback}


def _compliance_critic_route(state: REState) -> str:
    if state.get("_critic_approved"):
        return "compliance_drafter"
    if state.get("structure_attempt", 0) >= settings.MAX_CRITIC_RETRIES:
        return "compliance_drafter"
    return "compliance_structure"


def compliance_drafter_node(state: REState) -> dict:
    plan     = _safe(state, "structure_plan", {})
    research = _safe(state, "re_research", "")
    client   = _safe(state, "client_name", "")
    prop     = _safe(state, "property_address", "")

    system = (
        "You are a real estate compliance document writer. "
        "Draft the complete compliance document. "
        "Return JSON array of clause objects: [{heading, content, type, clause_ref}]. "
        "Return JSON only."
    )
    user = (
        f"Structure:\n{json.dumps(plan, indent=2, default=str)}\n\n"
        f"Client: {client}\nProperty: {prop}\nResearch:\n{research}\n\n"
        "Draft every section fully. Be specific to Indian real estate regulations."
    )
    raw = _chat([{"role": "system", "content": system}, {"role": "user", "content": user}],
                max_tokens=6000, json_mode=True)
    try:
        data = json.loads(raw)
        clauses = data if isinstance(data, list) else data.get("clauses", data.get("sections", []))
    except Exception:
        clauses = [{"heading": "Document", "content": raw, "type": "standard_clause"}]

    return {"clause_plan": clauses}


# ══════════════════════════════════════════════════════════════════════════════
# AGREEMENT PATH — single-shot
# ══════════════════════════════════════════════════════════════════════════════

def agreement_drafter_node(state: REState) -> dict:
    doc_type = _safe(state, "doc_type", "sale_deed")
    client   = _safe(state, "client_name", "")
    prop     = _safe(state, "property_address", "")
    research = _safe(state, "re_research", "")
    notes    = _safe(state, "special_notes", "")

    system = (
        "You are a real estate legal document drafter. "
        "Draft the complete agreement/deed with all clauses. "
        "Return JSON array: [{heading, content, type}]. Return JSON only."
    )
    user = (
        f"Document: {doc_type}\nParties: {client}\nProperty: {prop}\n"
        f"Special notes: {notes}\nResearch:\n{research}\n\n"
        "Draft all standard clauses per Indian law (Transfer of Property Act, Registration Act, Stamp Act). "
        "Include: recitals, consideration, property description, representations, "
        "conditions, covenants, stamp duty note, execution block."
    )
    raw = _chat([{"role": "system", "content": system}, {"role": "user", "content": user}],
                max_tokens=6000, json_mode=True)
    try:
        data = json.loads(raw)
        clauses = data if isinstance(data, list) else data.get("clauses", data.get("sections", []))
    except Exception:
        clauses = [{"heading": "Agreement", "content": raw, "type": "standard_clause"}]

    return {"clause_plan": clauses}


# ══════════════════════════════════════════════════════════════════════════════
# EVIDENCE — post-draft scan
# ══════════════════════════════════════════════════════════════════════════════

def evidence_scan_node(state: REState) -> dict:
    """
    The second half of the gate: what the model actually wrote.

    Pre-flight proved the property carries what the deliverable will need. This
    proves the drafted text asserts nothing beyond it — "clear and marketable
    title" is blocked when no chain exists, whatever the prompt said. Prompt
    instructions are a request; this is the enforcement.
    """
    from app.validators.evidenceValidator import EvidenceBundle, scan_assertions

    clauses = _safe(state, "clause_plan", [])
    if not clauses or not state.get("evidence_bundle"):
        return {}

    summary = state["evidence_bundle"]
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


def _evidence_scan_route(state: REState) -> str:
    return "blocked" if state.get("_blocked") else "renderer"


# ══════════════════════════════════════════════════════════════════════════════
# RENDERER / HEALER / UPLOAD
# ══════════════════════════════════════════════════════════════════════════════

def renderer_node(state: REState) -> dict:
    from app.services.render.docxRenderer import render
    try:
        path = render(
            clause_plan=_safe(state, "clause_plan", []),
            doc_type=_safe(state, "doc_type", "valuation_report"),
            client_name=_safe(state, "client_name", "Client"),
            property_address=_safe(state, "property_address", ""),
            computed=_safe(state, "computed", {}),
            header_image_path=_safe(state, "header_image_path"),
            job_id=state["_job_id"],
        )
        return {"doc_path": path, "render_error": None}
    except Exception as e:
        return {"doc_path": None, "render_error": str(e),
                "render_attempt": state.get("render_attempt", 0) + 1}


def _renderer_route(state: REState) -> str:
    if state.get("render_error") and state.get("render_attempt", 0) < settings.MAX_HEALER_RETRIES:
        return "healer"
    return "upload"


def healer_node(state: REState) -> dict:
    error   = state.get("render_error", "")
    clauses = _safe(state, "clause_plan", [])
    system  = (
        "You are a document repair agent. "
        "Given a render error and the clause plan, return a corrected clause plan as JSON array. "
        "Return JSON only."
    )
    user = f"Error:\n{error}\n\nClause plan (first 3):\n{json.dumps(clauses[:3], indent=2, default=str)}\n\nReturn corrected full clause plan."
    raw = _chat([{"role": "system", "content": system}, {"role": "user", "content": user}],
                max_tokens=4000, json_mode=True)
    try:
        data = json.loads(raw)
        fixed = data if isinstance(data, list) else data.get("clauses", clauses)
    except Exception:
        fixed = clauses
    return {"clause_plan": fixed, "render_error": None}


def upload_node(state: REState) -> dict:
    from app.services.storage.uploader import upload
    doc_path = state.get("doc_path")
    if not doc_path:
        return {"doc_url": None, "generation_errors": "No document generated"}
    try:
        url = upload(doc_path)
        return {"doc_url": url, "generation_errors": None}
    except Exception as e:
        return {"doc_url": f"file://{doc_path}", "generation_errors": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# BUILD GRAPH
# ══════════════════════════════════════════════════════════════════════════════

g = StateGraph(REState)

g.add_node("intake",                   intake_node)
g.add_node("property_data_parser",     property_data_parser_node)
g.add_node("valuation_calculator",     valuation_calculator_node)
g.add_node("research",                 research_node)
g.add_node("vision",                   vision_node)
g.add_node("evidence_check",           evidence_check_node)
g.add_node("evidence_scan",            evidence_scan_node)
g.add_node("rec_renderer",             rec_renderer_node)
g.add_node("valuation_structure",      valuation_structure_node)
g.add_node("valuation_critic",         valuation_critic_node)
g.add_node("section_drafter",          section_drafter_node)
g.add_node("compliance_structure",     compliance_structure_node)
g.add_node("compliance_critic",        compliance_critic_node)
g.add_node("compliance_drafter",       compliance_drafter_node)
g.add_node("agreement_drafter",        agreement_drafter_node)
g.add_node("renderer",                 renderer_node)
g.add_node("healer",                   healer_node)
g.add_node("upload",                   upload_node)

g.set_entry_point("intake")
g.add_edge("intake",               "property_data_parser")
g.add_edge("property_data_parser", "valuation_calculator")
g.add_edge("valuation_calculator", "research")
g.add_edge("research",             "vision")

# S8: the gate sits before the structure nodes, so a property that cannot
# support the report is refused before a token is spent drafting one. `blocked`
# ends the graph — there is deliberately no edge around it.
g.add_edge("vision", "evidence_check")
g.add_conditional_edges("evidence_check", _gated_route, {
    "blocked":             END,
    "rec_renderer":        "rec_renderer",
    "valuation_structure": "valuation_structure",
    "compliance_structure": "compliance_structure",
    "agreement_drafter":   "agreement_drafter",
})

# Reconciliation path — a rent roll states figures, not facts about title.
g.add_edge("rec_renderer", "evidence_scan")

# Valuation path
g.add_edge("valuation_structure", "valuation_critic")
g.add_conditional_edges("valuation_critic", _valuation_critic_route, {
    "valuation_structure": "valuation_structure",
    "section_drafter":     "section_drafter",
})
g.add_conditional_edges("section_drafter", _section_drafter_route, {
    "section_drafter": "section_drafter",
    "renderer":        "evidence_scan",
})

# Compliance path
g.add_edge("compliance_structure", "compliance_critic")
g.add_conditional_edges("compliance_critic", _compliance_critic_route, {
    "compliance_structure": "compliance_structure",
    "compliance_drafter":   "compliance_drafter",
})
g.add_edge("compliance_drafter", "evidence_scan")

# Agreement path
g.add_edge("agreement_drafter", "evidence_scan")

# S8, second half: what the model actually wrote. An assertion with nothing
# behind it ends the job here rather than being softened into hedged prose.
g.add_conditional_edges("evidence_scan", _evidence_scan_route, {
    "blocked":  END,
    "renderer": "renderer",
})

# Shared convergence
g.add_conditional_edges("renderer", _renderer_route, {
    "healer": "healer",
    "upload": "upload",
})
g.add_edge("healer", "renderer")
g.add_edge("upload", END)

app = g.compile()
