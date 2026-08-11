"""Auth controller — shapes what the service returns into a response."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories import userRepository
from app.schemas.request.authRequest import (
    GoogleSignInRequest,
    MfaRequest,
    SignInRequest,
    SignUpRequest,
)
from app.schemas.response.authResponse import AuthResponse, SessionUser
from app.services import authService
from app.services.access.scope import FirmScope
from app.services.authService import SignInResult


def _session_user(user: User | None) -> SessionUser | None:
    if user is None:
        return None
    return SessionUser(
        id=str(user.id),
        firm_id=str(user.firm_id),
        email=user.email,
        role=user.role,
        ibbi_reg_no=user.ibbi_reg_no,
        valuer_asset_class=user.valuer_asset_class,
        mfa_enabled=user.mfa_enabled,
    )


def _response(result: SignInResult) -> AuthResponse:
    return AuthResponse(
        mfa_required=result.mfa_required,
        access_token=result.access_token,
        mfa_token=result.mfa_token,
        totp_enrolment_uri=result.totp_enrolment_uri,
        user=_session_user(result.user),
    )


async def sign_up(db: AsyncSession, req: SignUpRequest) -> AuthResponse:
    return _response(
        await authService.sign_up(
            db,
            firm_name=req.firm_name,
            email=str(req.email),
            password=req.password,
            role=req.role,
            ibbi_reg_no=req.ibbi_reg_no,
            valuer_asset_class=req.valuer_asset_class,
        )
    )


async def sign_in(db: AsyncSession, req: SignInRequest) -> AuthResponse:
    return _response(await authService.sign_in(db, email=str(req.email), password=req.password))


async def sign_in_with_google(db: AsyncSession, req: GoogleSignInRequest) -> AuthResponse:
    return _response(await authService.sign_in_with_google(db, id_token=req.id_token))


async def verify_mfa(db: AsyncSession, user_id: uuid.UUID, req: MfaRequest) -> AuthResponse:
    return _response(await authService.verify_mfa(db, user_id=user_id, code=req.code))


async def me(db: AsyncSession, scope: FirmScope) -> SessionUser:
    user = await userRepository.get(db, scope, scope.user_id)
    if user is None:
        # The token verified but the row is gone. Treat it as no session at all.
        raise HTTPException(401, "Sign in again")
    session_user = _session_user(user)
    assert session_user is not None
    return session_user
