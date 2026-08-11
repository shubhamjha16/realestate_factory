"""
Properties.

Carries `geom` because comparable search is a spatial query — "sales within
2 km of this point in the last 18 months" — and a `LIKE` over an address column
is not that. The GiST index that makes it a query rather than a sequential scan
is **hand-written in the migration**: Alembic's autogenerate does not emit it,
and without it spatial search silently degrades as the table grows.

Areas are `NUMERIC`, not float. A rounded area multiplied by a rate is a wrong
value conclusion, and land parcels are quoted in units whose conversion factor
is itself state-dependent (S6).
"""

from __future__ import annotations

import uuid

from geoalchemy2 import Geography
from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Area, Base, TimestampMixin, uuid_pk

TENURES = ("freehold", "leasehold")


class Property(TimestampMixin, Base):
    __tablename__ = "properties"
    __table_args__ = (
        # Named explicitly so the migration's hand-written CREATE INDEX and this
        # model cannot drift apart under a later autogenerate.
        Index("ix_properties_geom", "geom", postgresql_using="gist"),
        Index("ix_properties_firm_city", "firm_id", "city"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    firm_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("firms.id", ondelete="CASCADE"), index=True
    )
    # FK added in S5 alongside the mandates table.
    mandate_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True))

    title: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    property_type: Mapped[str | None] = mapped_column(String(60))

    address: Mapped[str | None] = mapped_column(String(500))
    locality: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(60))
    pincode: Mapped[str | None] = mapped_column(String(10))

    geom: Mapped[str | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False)
    )

    survey_no: Mapped[str | None] = mapped_column(String(120))
    khasra_no: Mapped[str | None] = mapped_column(String(120))

    land_area: Mapped[float | None] = mapped_column(Area)
    land_area_unit: Mapped[str | None] = mapped_column(String(20))
    built_up_area: Mapped[float | None] = mapped_column(Area)
    carpet_area: Mapped[float | None] = mapped_column(Area)

    year_built: Mapped[int | None] = mapped_column(Integer)
    floors: Mapped[int | None] = mapped_column(Integer)
    tenure: Mapped[str | None] = mapped_column(String(20))
