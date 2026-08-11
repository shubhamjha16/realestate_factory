"""
Authorization decisions, stated once.

Kept separate from `scope.py` so the data and the rules do not blur: a scope
describes who is asking, these functions decide what that permits.
"""

from __future__ import annotations

from fastapi import HTTPException

from app.services.access.scope import FirmScope


def require_edit(scope: FirmScope) -> None:
    if not scope.may_edit:
        raise HTTPException(403, f"role {scope.role!r} may not create or modify records")


def require_review(scope: FirmScope) -> None:
    if not scope.may_review:
        raise HTTPException(403, f"role {scope.role!r} may not review deliverables")


def require_sign(scope: FirmScope, asset_class: str | None = None) -> None:
    """
    The sign-off gate's role half.

    S13 adds the rest: no deliverable may be signed with an open review note, and
    an unsigned export carries the "Draft — not for reliance" watermark. The
    registration check lives here from S5 because an analyst reaching a sign
    endpoint at all is the failure worth refusing earliest.
    """
    if not scope.may_sign:
        raise HTTPException(
            403,
            f"role {scope.role!r} may not sign a valuation; a partner or a "
            f"registered valuer must sign",
        )
    if not scope.ibbi_reg_no:
        raise HTTPException(
            403,
            "signing requires an IBBI registration number on the signer's account",
        )
    if asset_class and scope.valuer_asset_class != asset_class:
        raise HTTPException(
            403,
            f"signer is registered for {scope.valuer_asset_class!r}, not {asset_class!r}",
        )
