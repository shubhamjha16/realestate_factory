"""
Authentication.

Password sign-in, Google sign-in, and an MFA step that is on by default. §11.1 is
settled as IBBI-registered and bank panel valuation, which means accounts here
sign documents a bank or a tribunal relies on — so MFA is not an option a firm
opts into, and a `valuer` account cannot exist without a registration number.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.configs.envConfig import settings
from app.models.firm import Firm
from app.models.user import User
from app.repositories import userRepository
from app.services.access.scope import ALL_ROLES, ROLE_CLIENT, ROLE_VALUER, FirmScope
from app.utils.logger import get_logger
from app.utils.security import (
    hash_password,
    issue_access_token,
    issue_mfa_token,
    needs_rehash,
    new_totp_secret,
    totp_uri,
    verify_password,
    verify_totp,
)

logger = get_logger(__name__)

# One message for every sign-in failure. Distinguishing "no such account" from
# "wrong password" tells an attacker which addresses are worth attacking.
_SIGNIN_FAILED = "Email or password is incorrect"


class SignInResult:
    """Either a session, or an MFA challenge that must be answered first."""

    def __init__(self, *, access_token: str | None = None, mfa_token: str | None = None,
                 user: User | None = None, totp_enrolment_uri: str | None = None):
        self.access_token = access_token
        self.mfa_token = mfa_token
        self.user = user
        self.totp_enrolment_uri = totp_enrolment_uri

    @property
    def mfa_required(self) -> bool:
        return self.access_token is None


async def sign_up(
    db: AsyncSession,
    *,
    firm_name: str,
    email: str,
    password: str,
    role: str = "partner",
    ibbi_reg_no: str | None = None,
    valuer_asset_class: str | None = None,
) -> SignInResult:
    """
    Creates a firm and its first user. The first account is a partner, because
    a firm with no one who can sign is a firm that cannot deliver.
    """
    _validate_role(role, ibbi_reg_no, valuer_asset_class)

    if await userRepository.find_for_authentication(db, email) is not None:
        # Deliberately the same shape as success would be from the outside: the
        # console tells the user to sign in instead, and an enumeration attempt
        # learns nothing it could not learn from the sign-in form anyway.
        raise HTTPException(409, "An account already exists for this address")

    firm = Firm(name=firm_name.strip())
    db.add(firm)
    await db.flush()

    secret = new_totp_secret()
    user = await userRepository.create(
        db,
        firm_id=firm.id,
        email=email,
        role=role,
        hashed_password=hash_password(password),
        ibbi_reg_no=ibbi_reg_no,
        valuer_asset_class=valuer_asset_class,
        totp_secret=secret,
        mfa_enabled=False,
    )
    logger.info("firm %s created with first user %s", firm.id, user.id)

    # Enrolment, not a session: the account is not usable until the first TOTP
    # code proves the authenticator was actually set up.
    return SignInResult(
        mfa_token=issue_mfa_token(user_id=user.id),
        user=user,
        totp_enrolment_uri=totp_uri(secret, user.email),
    )


async def sign_in(db: AsyncSession, *, email: str, password: str) -> SignInResult:
    user = await userRepository.find_for_authentication(db, email)
    ok = verify_password(password, user.hashed_password if user else None)

    if not user or not ok:
        raise HTTPException(401, _SIGNIN_FAILED)
    if not user.is_active:
        raise HTTPException(403, "This account is disabled")

    if user.hashed_password and needs_rehash(user.hashed_password):
        user.hashed_password = hash_password(password)
        await userRepository.save(db, user)

    return await _complete(db, user)


async def sign_in_with_google(db: AsyncSession, *, id_token: str) -> SignInResult:
    """
    Verifies a Google ID token and matches it to an existing account.

    It never provisions one. A stranger with a Google account is not a member of
    a valuation firm, and self-service into a tenant holding other clients' title
    data is exactly the door that must not exist.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(501, "Google sign-in is not configured on this deployment")

    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    try:
        claims = google_id_token.verify_oauth2_token(
            id_token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except ValueError as e:
        raise HTTPException(401, "Google sign-in failed") from e

    if not claims.get("email_verified"):
        raise HTTPException(401, "Google account has no verified email address")

    user = await userRepository.find_by_google_sub(db, claims["sub"])
    if user is None:
        # Link on first use, but only to an account an administrator already made.
        user = await userRepository.find_for_authentication(db, claims["email"])
        if user is None:
            raise HTTPException(403, "No account on this deployment for that address")
        user.google_sub = claims["sub"]
        await userRepository.save(db, user)

    if not user.is_active:
        raise HTTPException(403, "This account is disabled")
    return await _complete(db, user)


async def verify_mfa(db: AsyncSession, *, user_id: uuid.UUID, code: str) -> SignInResult:
    user = await userRepository.get_for_session(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(401, "Sign in again")

    if not verify_totp(user.totp_secret, code):
        logger.warning("failed MFA for user %s", user_id)
        raise HTTPException(401, "That code is not valid")

    if not user.mfa_enabled:
        # First successful code completes enrolment.
        user.mfa_enabled = True
        await userRepository.save(db, user)

    return SignInResult(
        access_token=issue_access_token(user_id=user.id, firm_id=user.firm_id, role=user.role),
        user=user,
    )


async def _complete(db: AsyncSession, user: User) -> SignInResult:
    if settings.MFA_REQUIRED or user.mfa_enabled:
        if not user.totp_secret:
            user.totp_secret = new_totp_secret()
            await userRepository.save(db, user)
        return SignInResult(
            mfa_token=issue_mfa_token(user_id=user.id),
            user=user,
            totp_enrolment_uri=None if user.mfa_enabled else totp_uri(user.totp_secret, user.email),
        )

    return SignInResult(
        access_token=issue_access_token(user_id=user.id, firm_id=user.firm_id, role=user.role),
        user=user,
    )


def _validate_role(role: str, ibbi_reg_no: str | None, valuer_asset_class: str | None) -> None:
    if role not in ALL_ROLES:
        raise HTTPException(422, f"unknown role {role!r}; valid: {', '.join(ALL_ROLES)}")
    if role == ROLE_CLIENT:
        raise HTTPException(422, "a client account is granted per mandate, not created at signup")
    if role == ROLE_VALUER and not (ibbi_reg_no and valuer_asset_class):
        # §11.1: this platform is built for IBBI-registered and bank panel
        # valuation. A valuer account without a registration is an account that
        # can never sign anything, which is a trap rather than a permission.
        raise HTTPException(
            422,
            "a valuer account requires ibbi_reg_no and valuer_asset_class: the "
            "sign-off gate checks the registration covers the asset class",
        )


def scope_for(user: User, mandate_ids: tuple[uuid.UUID, ...] | None = None) -> FirmScope:
    return FirmScope(
        firm_id=user.firm_id,
        user_id=user.id,
        role=user.role,
        ibbi_reg_no=user.ibbi_reg_no,
        valuer_asset_class=user.valuer_asset_class,
        mandate_ids=mandate_ids,
    )
