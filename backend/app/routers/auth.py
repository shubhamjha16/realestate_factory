"""Auth routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.configs.dbConfig import get_db
from app.controllers import authController
from app.routers.deps import current_scope, mfa_subject
from app.schemas.request.authRequest import (
    GoogleSignInRequest,
    MfaRequest,
    SignInRequest,
    SignUpRequest,
)
from app.schemas.response.authResponse import AuthResponse, SessionUser
from app.services.access.scope import FirmScope

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, status_code=201)
async def signup(req: SignUpRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    return await authController.sign_up(db, req)


@router.post("/signin", response_model=AuthResponse)
async def signin(req: SignInRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    return await authController.sign_in(db, req)


@router.post("/google", response_model=AuthResponse)
async def google(req: GoogleSignInRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    return await authController.sign_in_with_google(db, req)


@router.post("/mfa", response_model=AuthResponse)
async def mfa(
    req: MfaRequest,
    user_id: uuid.UUID = Depends(mfa_subject),
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    return await authController.verify_mfa(db, user_id, req)


@router.get("/me", response_model=SessionUser)
async def me(
    scope: FirmScope = Depends(current_scope),
    db: AsyncSession = Depends(get_db),
) -> SessionUser:
    return await authController.me(db, scope)
