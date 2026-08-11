"""
Request dependencies.

`current_scope` is the only way a router obtains a `FirmScope`, and it is built
from a signed token — never from anything the caller can assert directly. There
is no header, query parameter or body field anywhere in this API that names a
firm id.
"""

from __future__ import annotations

import uuid

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.configs.dbConfig import get_db
from app.repositories import userRepository
from app.services.access.scope import FirmScope
from app.services.authService import scope_for
from app.utils.security import decode_token

bearer = HTTPBearer(auto_error=False)


async def current_scope(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> FirmScope:
    if credentials is None:
        raise HTTPException(401, "Authentication required")

    try:
        claims = decode_token(credentials.credentials, purpose="access")
    except jwt.PyJWTError as e:
        raise HTTPException(401, "Invalid or expired token") from e

    user = await userRepository.get_for_session(db, uuid.UUID(claims["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(401, "Invalid or expired token")

    # The token carries firm and role, but they are read from the row. A token
    # outlives a change of role, and the row is the truth about what someone may
    # do right now.
    return scope_for(user)


async def mfa_subject(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> uuid.UUID:
    """
    The half-authenticated identity, valid only against the MFA endpoint. Its
    `purpose` claim is checked, so it cannot be replayed against the real API.
    """
    if credentials is None:
        raise HTTPException(401, "Authentication required")
    try:
        claims = decode_token(credentials.credentials, purpose="mfa")
    except jwt.PyJWTError as e:
        raise HTTPException(401, "Invalid or expired token") from e
    return uuid.UUID(claims["sub"])
