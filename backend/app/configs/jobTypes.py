"""
Job types, grouped by the graph path that serves them.

Mirrored on the console by `frontend/src/shared/constants/jobTypes.ts`. The two
must not drift; from S3 the generated `packages/api-types` makes drift a build
failure rather than a runtime surprise.
"""

# Valuation path — section-by-section iterative drafting
VALUATION_TYPES = {
    "valuation_report",
    "due_diligence_report",
    "construction_disbursement_report",
}

# Compliance path — structure → critic loop → drafter
COMPLIANCE_TYPES = {
    "rera_registration",
    "rera_quarterly_report",
    "fema_compliance",
    "environment_impact_assessment",
    "noc_application",
}

# Agreement path — single-shot drafting
AGREEMENT_TYPES = {
    "sale_deed",
    "lease_agreement",
    "rental_agreement",
    "development_agreement",
    "mou",
    "power_of_attorney",
}

# Reconciliation path — deterministic, zero LLM
RECONCILIATION_TYPES = {
    "rent_roll_report",
    "portfolio_report",
}

ALL_JOB_TYPES = VALUATION_TYPES | COMPLIANCE_TYPES | AGREEMENT_TYPES | RECONCILIATION_TYPES

# Set iteration order is not stable across processes. Anything user-facing — a
# 422 listing the valid values, the console's dropdown — uses this instead.
ALL_JOB_TYPES_SORTED: tuple[str, ...] = tuple(sorted(ALL_JOB_TYPES))

PATH_BY_JOB_TYPE = {
    **{t: "valuation" for t in VALUATION_TYPES},
    **{t: "compliance" for t in COMPLIANCE_TYPES},
    **{t: "agreement" for t in AGREEMENT_TYPES},
    **{t: "reconciliation" for t in RECONCILIATION_TYPES},
}
