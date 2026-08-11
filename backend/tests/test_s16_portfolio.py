"""
Sprint 16 Portfolio Analytics, Rent Roll WAULT & Construction Disbursement Tests.

Verifies:
1. Rent roll total ties to sum of lines to the rupee, and WAULT matches hand calculation.
2. Construction disbursement request exceeding certified physical completion stage is flagged and blocked.
3. Portfolio concentration roll-up across properties by tenant, city, and asset class.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.portfolio.disbursement import verify_disbursement_request
from app.services.portfolio.rentRoll import compute_rent_roll_and_wault
from app.services.portfolio.rollup import compute_portfolio_rollup


def test_rent_roll_total_and_wault_calculation():
    """
    Verify rent roll total ties to line sum to the rupee and WAULT matches hand calculation.
    """
    ref_date = date(2026, 1, 1)

    leases = [
        # Lease 1: 2 years remaining (expiry 2028-01-01), Annual rent = 1,200,000
        {"tenant_name": "Tenant A", "area": 1000, "monthly_rent": Decimal("100000"), "lease_expiry": "2028-01-01"},
        # Lease 2: 4 years remaining (expiry 2030-01-01), Annual rent = 2,400,000
        {"tenant_name": "Tenant B", "area": 2000, "monthly_rent": Decimal("200000"), "lease_expiry": "2030-01-01"},
    ]

    res = compute_rent_roll_and_wault(leases, as_of_date=ref_date)

    # Monthly rent sum: 100,000 + 200,000 = 300,000
    assert res["total_monthly_rent"] == "300000.00"
    # Annual rent sum: 1,200,000 + 2,400,000 = 3,600,000
    assert res["total_annual_rent"] == "3600000.00"

    # Hand calculation of WAULT:
    # (2.0 * 1,200,000 + 4.0 * 2,400,000) / 3,600,000 = (2,400,000 + 9,600,000) / 3,600,000 = 12,000,000 / 3,600,000 = 3.333... ~ 3.33 years
    wault = float(res["wault_years"])
    assert abs(wault - 3.33) < 0.05


def test_disbursement_request_exceeding_certified_stage_flagged():
    """
    Verify disbursement request exceeding certified physical progress percentage is flagged and blocked.
    """
    # Case A: Certified = 65%, Prior = 50%, Requested = 20% -> Total 70% > 65% (BLOCKED)
    res_blocked = verify_disbursement_request(
        certified_stage_pct=Decimal("65.00"),
        requested_tranche_pct=Decimal("20.00"),
        prior_disbursed_pct=Decimal("50.00"),
    )
    assert res_blocked["approved"] is False
    assert res_blocked["status_code"] == "FLAGGED_EXCEEDS_CERTIFIED_STAGE"
    assert "exceeds certified physical completion stage" in res_blocked["message"]

    # Case B: Certified = 65%, Prior = 50%, Requested = 10% -> Total 60% <= 65% (APPROVED)
    res_approved = verify_disbursement_request(
        certified_stage_pct=Decimal("65.00"),
        requested_tranche_pct=Decimal("10.00"),
        prior_disbursed_pct=Decimal("50.00"),
    )
    assert res_approved["approved"] is True
    assert res_approved["status_code"] == "ELIGIBLE_FOR_DISBURSEMENT"


def test_portfolio_concentration_rollup():
    """Verify portfolio roll-up total asset value and concentration percentages."""
    props = [
        {"concluded_value": Decimal("100000000"), "built_up_area": Decimal("10000"), "city": "Mumbai", "property_type": "Commercial", "top_tenant": "Bank A"},
        {"concluded_value": Decimal("50000000"), "built_up_area": Decimal("5000"), "city": "Pune", "property_type": "Residential", "top_tenant": "Tech B"},
    ]

    res = compute_portfolio_rollup(props)
    assert res["total_properties"] == 2
    assert res["total_asset_value"] == "150000000.00"

    # Check city concentration shares: Mumbai = 100M/150M = 66.67%, Pune = 50M/150M = 33.33%
    mumbai_share = [c for c in res["concentration_by_city"] if c["name"] == "Mumbai"][0]
    assert mumbai_share["share_percentage"] == "66.67"
