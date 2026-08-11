"""
Portfolio analytics and disbursement router (S16).
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.routers.deps import current_scope
from app.services.access.scope import FirmScope
from app.services.portfolio import disbursement, rentRoll, rollup

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


class RentRollRequest(BaseModel):
    leases: list[dict[str, Any]]
    as_of_date: datetime.date | None = None


class PortfolioRollupRequest(BaseModel):
    properties: list[dict[str, Any]]


class DisbursementVerifyRequest(BaseModel):
    certified_stage_pct: Decimal
    requested_tranche_pct: Decimal
    prior_disbursed_pct: Decimal = Field(default=Decimal("0.00"))


@router.post("/rent-roll", response_model=dict[str, Any])
async def compute_rent_roll(
    req: RentRollRequest,
    scope: FirmScope = Depends(current_scope),
):
    return rentRoll.compute_rent_roll_and_wault(
        leases=req.leases,
        as_of_date=req.as_of_date,
    )


@router.post("/rollup", response_model=dict[str, Any])
async def compute_portfolio_rollup_endpoint(
    req: PortfolioRollupRequest,
    scope: FirmScope = Depends(current_scope),
):
    return rollup.compute_portfolio_rollup(
        properties=req.properties,
    )


@router.post("/disbursement/verify", response_model=dict[str, Any])
async def verify_disbursement_endpoint(
    req: DisbursementVerifyRequest,
    scope: FirmScope = Depends(current_scope),
):
    return disbursement.verify_disbursement_request(
        certified_stage_pct=req.certified_stage_pct,
        requested_tranche_pct=req.requested_tranche_pct,
        prior_disbursed_pct=req.prior_disbursed_pct,
    )
