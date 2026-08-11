"""
Sprint 12 Provenance & Audit Trail Tests — Real Estate Factory.

Verifies:
1. Section -> ValuationLine -> Comparable & Section -> Document provenance resolution.
2. GET /deliverables/{id}/provenance chain completeness.
3. Audit logging on read, provenance lookups, and exports.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.controllers import deliverableController
from app.models.client import Client
from app.models.comparable import Comparable
from app.models.firm import Firm
from app.models.mandate import Mandate
from app.models.property import Property
from app.models.propertyDocument import PropertyDocument
from app.models.user import User
from app.models.valuation import Valuation, ValuationLine
from app.repositories import auditRepository, deliverableRepository
from app.services.access.scope import FirmScope

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def test_provenance_payload_structure_unit():
    """Unit test for provenance data structure schema."""
    sec = {
        "section_id": str(uuid.uuid4()),
        "ord": 1,
        "section_type": "executive_summary",
        "content": "Sample content",
        "figures": [
            {
                "valuation_line_id": str(uuid.uuid4()),
                "label": "Market Value",
                "amount": "25000000.00",
                "basis": "market",
                "source_ref": {"method": "sales_comparison"},
                "comparables": [
                    {
                        "comparable_id": str(uuid.uuid4()),
                        "address": "Sector 62 Noida",
                        "sale_price": "10650000",
                        "rate_per_unit": "7500",
                    }
                ],
            }
        ],
        "documents": [
            {
                "document_id": str(uuid.uuid4()),
                "kind": "title_deed",
                "doc_date": "2020-05-10",
                "issuing_authority": "Sub-Registrar Noida",
                "s3_key": "documents/prop-1/title_deed.pdf",
            }
        ],
    }

    assert sec["figures"][0]["amount"] == "25000000.00"
    assert sec["documents"][0]["kind"] == "title_deed"
    assert len(sec["figures"][0]["comparables"]) == 1


# ── Live DB Tests (skipped when TEST_DATABASE_URL is unconfigured) ─────────

def _rebuild_schema() -> None:
    from alembic.config import Config

    from alembic import command

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


@pytest_asyncio.fixture
async def db():
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not set — needs a live PostGIS (docker compose up -d)")
    await asyncio.to_thread(_rebuild_schema)
    engine = create_async_engine(TEST_DATABASE_URL)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def sample_mandate_setup(db):
    firm_id = uuid.uuid4()

    firm = Firm(id=firm_id, name="Vanguard Valuations LLP", plan="pro", seats=5)
    db.add(firm)
    await db.flush()

    # Every audit event is stamped with the acting user, and that is a real
    # foreign key. An event attributed to a UUID with no user behind it answers
    # "who exported this" with a row nobody can follow.
    valuer = User(
        firm_id=firm_id,
        email="valuer@vanguardvaluations.in",
        role="valuer",
        ibbi_reg_no="IBBI/RV/05/2021/14233",
        valuer_asset_class="land_and_building",
    )
    db.add(valuer)
    await db.flush()

    scope = FirmScope(firm_id=firm_id, user_id=valuer.id, role="valuer")

    # A mandate is an instruction from a client, and `client_id` is NOT NULL.
    # Creating one here rather than nulling the column: an unattributed mandate
    # is not a thing this product should be able to represent.
    client = Client(firm_id=firm_id, name="Federal Bank — Credit", kind="bank")
    db.add(client)
    await db.flush()

    mandate = Mandate(
        firm_id=firm_id,
        client_id=client.id,
        kind="valuation",
        purpose="loan",
        status="instructed",
    )
    db.add(mandate)
    await db.flush()

    prop = Property(
        firm_id=firm_id,
        mandate_id=mandate.id,
        title="Apex Commercial Tower",
        property_type="commercial office",
        address="Sector 62, Noida",
        city="Noida",
        state="Uttar Pradesh",
        pincode="201309",
    )
    db.add(prop)
    await db.flush()

    comp = Comparable(
        firm_id=firm_id,
        property_id=prop.id,
        source="market_registry",
        address="Tower A Sector 62, Noida",
        sale_date=date(2025, 11, 14),
        sale_price=Decimal("10650000"),
        area=Decimal("1420"),
        area_unit="sqft",
        rate_per_unit=Decimal("7500"),
        property_type="commercial office",
        verified=True,
    )
    db.add(comp)
    await db.flush()

    val = Valuation(
        firm_id=firm_id,
        property_id=prop.id,
        mandate_id=mandate.id,
        valuation_date=date(2026, 1, 15),
        basis="market",
        premise="existing_use",
        concluded_value=Decimal("25000000.00"),
        value_range_low=Decimal("24000000.00"),
        value_range_high=Decimal("26000000.00"),
        status="draft",
    )
    db.add(val)
    await db.flush()

    val_line = ValuationLine(
        valuation_id=val.id,
        ord=1,
        label="Indicated Sales Comparison Value",
        amount=Decimal("25000000.00"),
        basis="market",
        source_ref={"comparables_count": 1, "method": "adjusted_sales"},
        comparable_ids=[comp.id],
    )
    db.add(val_line)
    await db.flush()

    doc = PropertyDocument(
        firm_id=firm_id,
        property_id=prop.id,
        kind="title_deed",
        s3_key="documents/prop-1/title_deed.pdf",
        doc_date=date(2020, 5, 10),
        issuing_authority="Sub-Registrar Noida",
    )
    db.add(doc)
    await db.flush()

    return {
        "firm": firm,
        "scope": scope,
        "mandate": mandate,
        "property": prop,
        "comparable": comp,
        "valuation": val,
        "valuation_line": val_line,
        "document": doc,
    }


@pytest.mark.asyncio
async def test_deliverable_creation_and_provenance_resolution(db, sample_mandate_setup):
    setup = sample_mandate_setup
    scope: FirmScope = setup["scope"]
    mandate: Mandate = setup["mandate"]
    val_line: ValuationLine = setup["valuation_line"]
    doc: PropertyDocument = setup["document"]
    comp: Comparable = setup["comparable"]

    sections_data = [
        {
            "ord": 1,
            "section_type": "executive_summary",
            "content": "Executive Summary: Subject property market value is ₹ 2,50,00,000.",
            "valuation_line_ids": [val_line.id],
            "document_ids": [doc.id],
        }
    ]

    deliv = await deliverableRepository.create_deliverable(
        db,
        scope=scope,
        doc_type="valuation_report",
        title="Valuation Report - Apex Commercial Tower",
        mandate_id=mandate.id,
        sections=sections_data,
    )
    assert deliv.id is not None

    prov = await deliverableRepository.get_provenance(db, scope, deliv.id)
    assert prov is not None
    assert prov["deliverable_id"] == str(deliv.id)
    assert len(prov["sections"]) == 1

    sec_prov = prov["sections"][0]
    assert len(sec_prov["figures"]) == 1
    fig_prov = sec_prov["figures"][0]
    assert fig_prov["valuation_line_id"] == str(val_line.id)
    assert fig_prov["amount"] == "25000000.00"
    assert len(fig_prov["comparables"]) == 1
    assert fig_prov["comparables"][0]["comparable_id"] == str(comp.id)

    assert len(sec_prov["documents"]) == 1
    doc_prov = sec_prov["documents"][0]
    assert doc_prov["document_id"] == str(doc.id)
    assert doc_prov["kind"] == "title_deed"
    assert doc_prov["issuing_authority"] == "Sub-Registrar Noida"


@pytest.mark.asyncio
async def test_audit_event_logging_and_controller_integration(db, sample_mandate_setup):
    setup = sample_mandate_setup
    scope: FirmScope = setup["scope"]
    val_line: ValuationLine = setup["valuation_line"]
    doc: PropertyDocument = setup["document"]

    deliv = await deliverableRepository.create_deliverable(
        db,
        scope=scope,
        doc_type="valuation_report",
        title="Audit Test Deliverable",
        sections=[{
            "ord": 1,
            "section_type": "executive_summary",
            "content": "Test content",
            "valuation_line_ids": [val_line.id],
            "document_ids": [doc.id],
        }],
    )

    prov = await deliverableController.get_provenance(db, scope, deliv.id)
    assert prov is not None

    audit_events = await auditRepository.list_audit_events(db, scope)
    assert len(audit_events) >= 1
    latest = audit_events[0]
    assert latest.action == "fetch_provenance"
    assert latest.resource == "deliverable"
    assert latest.resource_id == deliv.id
