"""
Statutory compliance router (S14).
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.routers.deps import current_scope
from app.services.access.scope import FirmScope
from app.services.compliance import approvals, rera, stampDuty

router = APIRouter(prefix="/compliance", tags=["compliance"])


class ReraObligationsRequest(BaseModel):
    state: str = Field(..., min_length=2)
    rera_reg_date: datetime.date
    project_end_date: datetime.date


class StampDutyRequest(BaseModel):
    state: str = Field(..., min_length=2)
    document_type: str = Field(default="sale_deed")
    consideration: Decimal
    circle_rate: Decimal
    area: Decimal
    gender: str = Field(default="male")


class ApprovalsExpiringRequest(BaseModel):
    approvals: list[dict[str, Any]]
    within_days: int = Field(default=90, ge=1)


@router.post("/rera/obligations", response_model=list[dict[str, Any]])
async def get_rera_obligations(
    req: ReraObligationsRequest,
    scope: FirmScope = Depends(current_scope),
):
    return rera.generate_quarterly_obligations(
        state=req.state,
        rera_reg_date=req.rera_reg_date,
        project_end_date=req.project_end_date,
    )


@router.post("/stamp-duty", response_model=dict[str, Any])
async def compute_stamp_duty_endpoint(
    req: StampDutyRequest,
    scope: FirmScope = Depends(current_scope),
):
    return stampDuty.compute_stamp_duty(
        state=req.state,
        document_type=req.document_type,
        consideration=req.consideration,
        circle_rate=req.circle_rate,
        area=req.area,
        gender=req.gender,
    )


@router.post("/approvals/expiring", response_model=list[dict[str, Any]])
async def check_expiring_approvals_endpoint(
    req: ApprovalsExpiringRequest,
    scope: FirmScope = Depends(current_scope),
):
    return approvals.check_approvals_expiring_soon(
        approvals=req.approvals,
        within_days=req.within_days,
    )
