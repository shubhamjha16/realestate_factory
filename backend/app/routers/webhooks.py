"""
Webhooks and Quotas router (S18).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.routers.deps import current_scope
from app.services.access.scope import FirmScope
from app.services.integration import quotas, webhookService

router = APIRouter(tags=["integration"])


class DeliverWebhookRequest(BaseModel):
    url: str = Field(..., min_length=5)
    secret: str = Field(..., min_length=4)
    event_type: str = Field(default="valuation.completed")
    payload: dict[str, Any] = Field(default_factory=dict)
    simulate_failures: int = Field(default=0, ge=0)


class VerifyWebhookRequest(BaseModel):
    secret: str = Field(..., min_length=4)
    timestamp: int
    raw_body: str
    signature: str


@router.post("/api/v1/webhooks/deliver", response_model=dict[str, Any])
async def deliver_webhook_endpoint(
    req: DeliverWebhookRequest,
    scope: FirmScope = Depends(current_scope),
):
    return webhookService.deliver_webhook(
        url=req.url,
        secret=req.secret,
        event_type=req.event_type,
        payload=req.payload,
        simulate_failures=req.simulate_failures,
    )


@router.post("/api/v1/webhooks/verify", response_model=dict[str, Any])
async def verify_webhook_endpoint(
    req: VerifyWebhookRequest,
    scope: FirmScope = Depends(current_scope),
):
    is_valid = webhookService.verify_signature(
        secret=req.secret,
        timestamp=req.timestamp,
        body=req.raw_body,
        signature=req.signature,
    )
    return {
        "valid": is_valid,
        "message": "Signature verified successfully" if is_valid else "Signature verification failed: payload tampered or secret mismatch",
    }


@router.get("/api/v1/quotas/check", response_model=dict[str, Any])
async def check_quota_endpoint(
    plan: str = "starter",
    usage: int = 0,
    scope: FirmScope = Depends(current_scope),
):
    return quotas.check_plan_quota(plan=plan, current_usage=usage)
