"""
Configuration — Real Estate Factory
"""

import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY      = os.environ.get("GROQ_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY", "")
WEBHOOK_URL       = os.environ.get("WEBHOOK_URL", "")
S3_BUCKET         = os.environ.get("S3_BUCKET", "")
AWS_REGION        = os.environ.get("AWS_REGION", "ap-south-1")
OUTPUT_DIR        = os.environ.get("OUTPUT_DIR", "output")

# ── Job types by path ──────────────────────────────────────────────────────────

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

MAX_CRITIC_RETRIES = 2
MAX_HEALER_RETRIES = 2
