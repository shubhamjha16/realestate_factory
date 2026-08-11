"""
Password hashing, tokens, TOTP, and S20 security utilities.

Argon2id for passwords: memory-hard verification constant-time rehashing.
XLSX Formula Injection Neutralizer, Client Location Privacy Filter, and Authorization Matrix.
"""

from __future__ import annotations

import base64
import copy
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
_DUMMY_HASH = _hasher.hash("timing-equaliser")

ACCESS_TOKEN_TTL = timedelta(hours=8)
MFA_TOKEN_TTL = timedelta(minutes=5)

TOKEN_ALGORITHM = "HS256"
TOKEN_AUDIENCE = "realestate-factory"


# ── passwords ─────────────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str | None) -> bool:
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
    return pyotp.TOTP(secret).verify(code.strip().replace(" ", ""), valid_window=1)


def new_recovery_code() -> str:
    return base64.b32encode(os.urandom(10)).decode("ascii").rstrip("=")


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


# ── Sprint 20 Security & Authorization ───────────────────────────────────────

AUTH_MATRIX: dict[str, dict[str, list[str]]] = {
    "admin": {
        "mandates": ["read", "write", "delete"],
        "jobs": ["read", "write", "delete"],
        "deliverables": ["read", "write", "sign", "export", "delete"],
        "audit_logs": ["read"],
    },
    "valuer": {
        "mandates": ["read", "write"],
        "jobs": ["read", "write"],
        "deliverables": ["read", "write", "sign", "export"],
        "audit_logs": ["read"],
    },
    "analyst": {
        "mandates": ["read", "write"],
        "jobs": ["read", "write"],
        "deliverables": ["read", "write", "export"],
        "audit_logs": [],
    },
    "client": {
        "mandates": ["read"],
        "jobs": ["read"],
        "deliverables": ["read", "export"],
        "audit_logs": [],
    },
}


def sanitize_excel_cell(value: Any) -> Any:
    """
    Neutralize Excel formula injection in user-supplied strings.
    If a string starts with `=`, `+`, `-`, `@`, `\\t`, `\\r`, prefix with `'` (single quote).
    """
    if not isinstance(value, str):
        return value

    s = value.strip()
    if s.startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
        return f"'{value}"

    return value


def filter_client_role_response(data: dict[str, Any]) -> dict[str, Any]:
    """
    Filter API responses for `client` role users to strip exact GPS coordinates
    and sensitive owner details for location privacy.
    """
    clean_data = copy.deepcopy(data)

    sensitive_keys = {
        "latitude",
        "longitude",
        "coordinates",
        "exact_gps",
        "owner_name",
        "owner_details",
        "owner",
    }

    def _recursive_strip(node: Any) -> Any:
        if isinstance(node, dict):
            return {
                k: _recursive_strip(v)
                for k, v in node.items()
                if k.lower() not in sensitive_keys
            }
        elif isinstance(node, list):
            return [_recursive_strip(item) for item in node]
        return node

    return _recursive_strip(clean_data)


def verify_authorization(role: str, resource: str, action: str) -> bool:
    """
    Verify permission against the programmatically defined authorization matrix.
    """
    role_clean = (role or "").lower().strip()
    resource_clean = (resource or "").lower().strip()
    action_clean = (action or "").lower().strip()

    role_perms = AUTH_MATRIX.get(role_clean, {})
    resource_actions = role_perms.get(resource_clean, [])

    return action_clean in resource_actions
