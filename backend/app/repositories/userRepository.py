"""
User repository.

Sign-in is the one place that must read a user *before* a scope exists, so
`find_for_authentication` is explicitly unscoped and named to say so. Everything
else takes a `FirmScope`.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.access.scope import FirmScope


async def find_for_authentication(db: AsyncSession, email: str) -> User | None:
    """
    Unscoped by necessity: at sign-in there is no session to scope by.

    Email is matched case-insensitively. It returns inactive users too, so that
    the caller can refuse a disabled account explicitly rather than letting it
    look like a wrong password.
    """
    stmt = select(User).where(func.lower(User.email) == email.strip().lower())
    return (await db.execute(stmt)).scalar_one_or_none()


async def find_by_google_sub(db: AsyncSession, google_sub: str) -> User | None:
    """Unscoped for the same reason: this is the OAuth callback's first read."""
    return (
        await db.execute(select(User).where(User.google_sub == google_sub))
    ).scalar_one_or_none()


async def get_for_session(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """
    Unscoped: this *builds* the scope, from a signed token's subject. It cannot
    take the scope it is about to produce.
    """
    return await db.get(User, user_id)


async def get(db: AsyncSession, scope: FirmScope, user_id: uuid.UUID) -> User | None:
    stmt = select(User).where(User.id == user_id, User.firm_id == scope.firm_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_users(db: AsyncSession, scope: FirmScope, *, limit: int = 100) -> list[User]:
    stmt = (
        select(User)
        .where(User.firm_id == scope.firm_id)
        .order_by(User.email)
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars())


async def create(
    db: AsyncSession,
    *,
    firm_id: uuid.UUID,
    email: str,
    role: str,
    hashed_password: str | None = None,
    google_sub: str | None = None,
    ibbi_reg_no: str | None = None,
    valuer_asset_class: str | None = None,
    totp_secret: str | None = None,
    mfa_enabled: bool = False,
) -> User:
    """
    Unscoped: signup creates the first user of a firm, before any scope exists.
    Adding a colleague goes through `usersController`, which supplies the scope's
    firm id as `firm_id` — it never lets a caller name a different one.
    """
    user = User(
        firm_id=firm_id,
        email=email.strip().lower(),
        role=role,
        hashed_password=hashed_password,
        google_sub=google_sub,
        ibbi_reg_no=ibbi_reg_no,
        valuer_asset_class=valuer_asset_class,
        totp_secret=totp_secret,
        mfa_enabled=mfa_enabled,
    )
    db.add(user)
    await db.flush()
    await db.commit()
    await db.refresh(user)
    return user


async def save(db: AsyncSession, user: User) -> User:
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
