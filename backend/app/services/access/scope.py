"""
The firm scope.

Tenancy is enforced at the repository layer, never the router. That is not a
style preference: routers multiply, and a rule enforced in one router is a rule
the next router does not know about. This system holds several clients' title
and transaction data in one database, and the only defensible place for the
boundary is the last layer before SQL.

Every repository function in this codebase takes a `FirmScope` and filters by
it. `tests/test_repository_scope_guard.py` fails the build if one does not.

Denials are 404, not 403. "You may not read this" tells the caller the row
exists, which for a mandate name or a property address is itself the leak.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

# §11.1, settled: IBBI-registered valuation and bank panel valuation.
ROLE_PARTNER = "partner"
ROLE_VALUER = "valuer"
ROLE_ANALYST = "analyst"
ROLE_READONLY = "readonly"
ROLE_CLIENT = "client"

ALL_ROLES = (ROLE_PARTNER, ROLE_VALUER, ROLE_ANALYST, ROLE_READONLY, ROLE_CLIENT)

# Who may sign a valuation. Being in this set is necessary, not sufficient —
# S13 also checks the signer's registration covers the asset class and that no
# review note is open.
ROLES_THAT_MAY_SIGN = frozenset({ROLE_PARTNER, ROLE_VALUER})
ROLES_THAT_MAY_REVIEW = frozenset({ROLE_PARTNER, ROLE_VALUER})
ROLES_THAT_MAY_EDIT = frozenset({ROLE_PARTNER, ROLE_VALUER, ROLE_ANALYST})


@dataclass(frozen=True)
class FirmScope:
    """
    Who is asking, and what they are allowed to see.

    Frozen because a scope that can be mutated after an authorization decision
    is not a scope.
    """

    firm_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    ibbi_reg_no: str | None = None
    valuer_asset_class: str | None = None
    # A `client` user sees exactly the mandates they were granted and nothing
    # else — not their firm's other work, and never another firm's (S16).
    mandate_ids: tuple[uuid.UUID, ...] | None = None

    @property
    def is_client(self) -> bool:
        return self.role == ROLE_CLIENT

    @property
    def may_sign(self) -> bool:
        return self.role in ROLES_THAT_MAY_SIGN

    @property
    def may_review(self) -> bool:
        return self.role in ROLES_THAT_MAY_REVIEW

    @property
    def may_edit(self) -> bool:
        return self.role in ROLES_THAT_MAY_EDIT

    def covers_mandate(self, mandate_id: uuid.UUID | None) -> bool:
        if not self.is_client:
            return True
        if mandate_id is None or self.mandate_ids is None:
            return False
        return mandate_id in self.mandate_ids


class ScopeRequired(RuntimeError):
    """
    Raised when a repository is reached without a scope.

    Never expected at runtime — the type system and the guard test make it
    unreachable. It exists so that if someone does find a way, the failure is
    loud rather than a query that quietly returns another firm's rows.
    """
