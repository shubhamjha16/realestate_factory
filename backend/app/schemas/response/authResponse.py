"""Auth response schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class SessionUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    firm_id: str
    email: str
    role: str
    ibbi_reg_no: str | None = None
    valuer_asset_class: str | None = None
    mfa_enabled: bool = False


class AuthResponse(BaseModel):
    """
    Either a session or a challenge, never both.

    `mfa_required` tells the console which it received. `totp_enrolment_uri` is
    present only while enrolling and never again — it carries the shared secret.
    """

    mfa_required: bool
    access_token: str | None = None
    mfa_token: str | None = None
    totp_enrolment_uri: str | None = None
    user: SessionUser | None = None


class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    kind: str


class MandateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    client_id: str
    kind: str
    purpose: str
    status: str
    instructed_on: date | None = None
    due_on: date | None = None
    valuer_id: str | None = None
    created_at: datetime | None = None
    requires_registered_valuer: bool = False
