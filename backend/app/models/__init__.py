"""
Model registry.

Importing this module registers every model on `Base.metadata`, which is what
Alembic's autogenerate and the money-column schema test both read. A model that
is not imported here is invisible to both — so a new model file goes in this
list in the same commit that creates it.
"""

from app.models.base import Area, Money, Percent
from app.models.client import CLIENT_KINDS, Client
from app.models.comparable import (
    ADJUSTMENT_FACTORS,
    Comparable,
    ComparableAdjustment,
)
from app.models.firm import Firm
from app.models.job import JOB_STATUSES, TERMINAL_STATUSES, Job
from app.models.mandate import (
    MANDATE_KINDS,
    MANDATE_PURPOSES,
    MANDATE_STATUSES,
    PURPOSES_REQUIRING_REGISTERED_VALUER,
    Mandate,
)
from app.models.property import TENURES, Property
from app.models.propertyDocument import (
    APPROVAL_KINDS,
    DOCUMENT_KINDS,
    ENCUMBRANCE_KINDS,
    Approval,
    Encumbrance,
    PropertyDocument,
    TitleChainEntry,
)
from app.models.user import USER_ROLES, User
from app.models.valuation import (
    APPROACH_METHODS,
    VALUATION_BASES,
    VALUATION_PREMISES,
    VALUATION_STATUSES,
    Valuation,
    ValuationApproach,
    ValuationLine,
)

__all__ = [
    "Area",
    "Money",
    "Percent",
    "Firm",
    "Client",
    "CLIENT_KINDS",
    "Comparable",
    "ComparableAdjustment",
    "ADJUSTMENT_FACTORS",
    "Mandate",
    "MANDATE_KINDS",
    "MANDATE_PURPOSES",
    "MANDATE_STATUSES",
    "PURPOSES_REQUIRING_REGISTERED_VALUER",
    "User",
    "USER_ROLES",
    "Job",
    "JOB_STATUSES",
    "TERMINAL_STATUSES",
    "Property",
    "TENURES",
    "PropertyDocument",
    "DOCUMENT_KINDS",
    "TitleChainEntry",
    "Encumbrance",
    "ENCUMBRANCE_KINDS",
    "Approval",
    "APPROVAL_KINDS",
    "Valuation",
    "ValuationApproach",
    "ValuationLine",
    "VALUATION_BASES",
    "VALUATION_PREMISES",
    "VALUATION_STATUSES",
    "APPROACH_METHODS",
]
