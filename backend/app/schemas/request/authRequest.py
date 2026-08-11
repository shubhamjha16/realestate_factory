"""Auth request schemas."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field

from app.services.access.scope import ALL_ROLES

RoleLiteral = Literal[ALL_ROLES]  # type: ignore[valid-type]

# Long enough that a passphrase is the natural choice. Composition rules push
# people towards Password1! and a sticky note; length does not.
Password = Annotated[str, Field(min_length=12, max_length=200)]


class SignUpRequest(BaseModel):
    firm_name: Annotated[str, Field(min_length=1, max_length=200)]
    email: EmailStr
    password: Password
    role: RoleLiteral = "partner"
    ibbi_reg_no: str | None = None
    valuer_asset_class: str | None = None


class SignInRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=1, max_length=200)]


class GoogleSignInRequest(BaseModel):
    id_token: Annotated[str, Field(min_length=1)]


class MfaRequest(BaseModel):
    code: Annotated[str, Field(min_length=6, max_length=10)]


class CreateClientRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    kind: Literal["bank", "developer", "nbfc", "fund", "individual"]


class CreateMandateRequest(BaseModel):
    client_id: str
    kind: Literal["valuation", "due_diligence", "rera", "transaction", "portfolio"]
    # Not defaultable: purpose drives the basis of value the report must be
    # prepared on, and from S9 which approaches are mandatory.
    purpose: Literal["loan", "ibc", "dispute", "financial_reporting", "internal"]
    instructed_on: str | None = None
    due_on: str | None = None
    valuer_id: str | None = None
