"""
Sprint 14 RERA, Stamp Duty, and Approvals Compliance Tests.

Verifies:
1. State-wise quarterly RERA obligation schedule & due dates.
2. Stamp duty calculation with circle-rate floor rule (max(consideration, circle_valuation)) for Maharashtra & Delhi.
3. 90-day approvals expiry warning engine.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.services.compliance.approvals import check_approvals_expiring_soon
from app.services.compliance.rera import generate_quarterly_obligations
from app.services.compliance.stampDuty import compute_stamp_duty


def test_rera_quarterly_obligations_generation():
    """Verify quarterly RERA obligation due dates for Maharashtra (MahaRERA)."""
    reg_date = date(2025, 1, 15)
    end_date = date(2026, 6, 30)

    obligations = generate_quarterly_obligations(
        state="maharashtra",
        rera_reg_date=reg_date,
        project_end_date=end_date,
    )

    assert len(obligations) >= 5
    assert "MahaRERA" in obligations[0]["authority"]
    
    # Q1 2025 due date must be 2025-04-15
    q1_2025 = [o for o in obligations if "Q1 (Jan - Mar) 2025" in o["period"]][0]
    assert q1_2025["due_date"] == "2025-04-15"

    # Q4 2025 due date must be 2026-01-15
    q4_2025 = [o for o in obligations if "Q4 (Oct - Dec) 2025" in o["period"]][0]
    assert q4_2025["due_date"] == "2026-01-15"


def test_stamp_duty_circle_rate_floor():
    """
    Verify stamp duty calculation and circle-rate floor rule across 2 states.
    """
    # Case A: Maharashtra — Agreed consideration (₹2.5 Cr) > Circle valuation (₹1.8 Cr)
    res_mh = compute_stamp_duty(
        state="maharashtra",
        document_type="sale_deed",
        consideration=Decimal("25000000"),
        circle_rate=Decimal("18000"),
        area=Decimal("1000"),
        gender="male",
    )
    assert res_mh["applied_basis"] == "agreed_consideration"
    assert res_mh["taxable_value"] == "25000000.00"
    assert res_mh["stamp_duty_amount"] == "1250000.00"  # 5% of 2.5 Cr

    # Case B: Delhi — Agreed consideration (₹1.2 Cr) < Circle valuation (₹1.5 Cr) -> Circle Rate Floor Applied
    res_dl = compute_stamp_duty(
        state="delhi",
        document_type="sale_deed",
        consideration=Decimal("12000000"),
        circle_rate=Decimal("15000"),
        area=Decimal("1000"),
        gender="male",
    )
    assert res_dl["applied_basis"] == "circle_rate_floor"
    assert res_dl["taxable_value"] == "15000000.00"  # 15,000 * 1,000
    assert res_dl["stamp_duty_amount"] == "900000.00"   # 6% of 1.5 Cr


def test_approvals_expiring_within_90_days():
    """Verify statutory approvals expiring within 90 days are flagged."""
    today = date.today()

    app_expiring_soon = {
        "kind": "fire_noc",
        "issuing_authority": "Chief Fire Officer",
        "valid_until": (today + timedelta(days=45)).isoformat(),
    }
    app_valid_long = {
        "kind": "occupation_certificate",
        "issuing_authority": "Municipal Corporation",
        "valid_until": (today + timedelta(days=365)).isoformat(),
    }

    flagged = check_approvals_expiring_soon([app_expiring_soon, app_valid_long], ref_date=today, within_days=90)

    assert len(flagged) == 1
    assert flagged[0]["kind"] == "fire_noc"
    assert flagged[0]["days_remaining"] == 45
    assert flagged[0]["is_expiring_soon"] is True
