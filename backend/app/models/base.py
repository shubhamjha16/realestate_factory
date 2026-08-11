"""
Column conventions shared by every model.

`Money` is the important one. Property values run to crores; a `float8` column
produces figures that will not reconcile across a portfolio and a rent roll that
should tie will not. There is no float money in this schema, and
`tests/test_schema_money.py` fails the build if one appears.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Declarative base for every model.

    Lives here rather than in `configs/dbConfig.py` so that reading the schema —
    which is what Alembic's autogenerate and the money-column guard both do —
    does not require a database URL or a provider key.
    """


# Every monetary column in this schema. 18 digits with 2 after the point holds
# ₹9,999,999,999,999,999.99 — comfortably past any Indian property portfolio.
Money = Numeric(18, 2)
MONEY_PRECISION = 18
MONEY_SCALE = 2

# Areas and percentages are exact too: a rounded area multiplied by a rate is a
# wrong value conclusion, and adjustment percentages compound.
Area = Numeric(18, 4)
Percent = Numeric(9, 4)


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UpdatedAtMixin:
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
