"""
Model registry.

Importing this module registers every model on `Base.metadata`, which is what
Alembic's autogenerate and the money-column schema test both read. A model that
is not imported here is invisible to both — so a new model file goes in this
list in the same commit that creates it.
"""

from app.models.base import Area, Money, Percent
from app.models.firm import Firm
from app.models.job import JOB_STATUSES, TERMINAL_STATUSES, Job
from app.models.property import TENURES, Property
from app.models.user import USER_ROLES, User

__all__ = [
    "Area",
    "Money",
    "Percent",
    "Firm",
    "User",
    "USER_ROLES",
    "Job",
    "JOB_STATUSES",
    "TERMINAL_STATUSES",
    "Property",
    "TENURES",
]
