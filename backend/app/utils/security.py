"""
Password hashing, tokens and TOTP.

Argon2id for passwords: it is memory-hard, so an attacker with a stolen dump
cannot trade GPUs for speed the way they can against bcrypt. Verification is
constant-time and rehashes transparently when the parameters change.
"""

from __future__ import annotations

import base64
import hmac
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.configs.envConfig import settings

_hasher = PasswordHasher()

# Verified against when no stored hash exists, so that a request for an unknown
# account costs the same as one for a known account. Without it the difference
# is measurable, and a measurable difference enumerates users.
_DUMMY_HASH = _hasher.hash("timing-equaliser")

ACCESS_TOKEN_TTL = timedelta(hours=8)
# Issued after password verification and before MFA. Short, single-purpose, and
# useless against any endpoint other than the MFA challenge.
MFA_TOKEN_TTL = timedelta(minutes=5)

TOKEN_ALGORITHM = "HS256"
TOKEN_AUDIENCE = "realestate-factory"


# ── passwords ─────────────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str | None) -> bool:
    """
    False rather than raising, for any reason.

    The dummy verify on a missing hash is deliberate: without it, a request for
    an account that does not exist returns measurably faster than one that does,
    and that difference enumerates users.
    """
    if not hashed:
        try:
            _hasher.verify(_DUMMY_HASH, password)
        except (VerifyMismatchError, InvalidHashError):
            pass
        return False
    try:
        return _hasher.verify(hashed, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    try:
        return _hasher.check_needs_rehash(hashed)
    except InvalidHashError:
        return True


# ── tokens ────────────────────────────────────────────────────────────────────


def _encode(claims: dict[str, Any], ttl: timedelta, purpose: str) -> str:
    now = datetime.now(UTC)
    payload = {
        **claims,
        "iat": now,
        "exp": now + ttl,
        "aud": TOKEN_AUDIENCE,
        "purpose": purpose,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=TOKEN_ALGORITHM)


def issue_access_token(*, user_id: uuid.UUID, firm_id: uuid.UUID, role: str) -> str:
    return _encode(
        {"sub": str(user_id), "firm": str(firm_id), "role": role}, ACCESS_TOKEN_TTL, "access"
    )


def issue_mfa_token(*, user_id: uuid.UUID) -> str:
    return _encode({"sub": str(user_id)}, MFA_TOKEN_TTL, "mfa")


def decode_token(token: str, *, purpose: str) -> dict[str, Any]:
    """
    Raises `jwt.PyJWTError` on anything wrong — expired, wrong audience, wrong
    signature, or a token issued for a different purpose. The purpose check is
    what stops a pre-MFA token being replayed against the real API.
    """
    claims = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[TOKEN_ALGORITHM],
        audience=TOKEN_AUDIENCE,
        options={"require": ["exp", "iat", "sub", "aud"]},
    )
    if claims.get("purpose") != purpose:
        raise jwt.InvalidTokenError(
            f"token issued for {claims.get('purpose')!r}, not {purpose!r}"
        )
    return claims


# ── MFA ───────────────────────────────────────────────────────────────────────


def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="Real Estate Factory")


def verify_totp(secret: str | None, code: str) -> bool:
    if not secret or not code:
        return False
    # One step of drift either way: phones are not perfectly in sync, and a
    # valuer who has to retype a code twice starts writing them down.
    return pyotp.TOTP(secret).verify(code.strip().replace(" ", ""), valid_window=1)


def new_recovery_code() -> str:
    return base64.b32encode(os.urandom(10)).decode("ascii").rstrip("=")


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)
