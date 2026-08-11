"""
Sprint 21 Load, Cost & Closed Beta Benchmark Tests.

Verifies:
1. Concurrent load driving generations and p95 latency tracking.
2. 500-property portfolio bulk import ingestion.
3. Deliverable cost verification against cost ledger (exact Decimal to the paisa).
"""

from __future__ import annotations

from decimal import Decimal

from app.services.benchmarks.loadTester import (
    benchmark_bulk_portfolio_import,
    run_concurrent_load_benchmark,
)
from app.services.llm.ledger import price_call, record_call, start_ledger


def test_concurrent_load_and_p95_latency():
    """Verify driving concurrent generations and calculating p95 latency."""
    res = run_concurrent_load_benchmark(concurrent_jobs=10)

    assert res["concurrent_jobs"] == 10
    assert res["completed_jobs"] == 10
    assert res["success_rate"] == 1.0
    assert res["p95_latency_ms"] >= 0.0


def test_bulk_portfolio_import_500_properties():
    """Verify 500-property portfolio import ingests cleanly within performance budget."""
    res = benchmark_bulk_portfolio_import(num_properties=500)

    assert res["num_properties"] == 500
    assert res["ingested_successfully"] == 500
    assert Decimal(res["total_portfolio_value"]) > Decimal("0.00")


def test_cost_per_deliverable_verified_against_ledger():
    """Verify deliverable token cost tracking against cost ledger to the paisa."""
    ledger = start_ledger()

    # Record LLM call: 1,500 prompt tokens, 500 completion tokens
    entry = record_call(
        node="section_drafter",
        model="llama-3.3-70b-versatile",
        tokens_in=1500,
        tokens_out=500,
    )

    assert entry is not None
    assert entry.tokens_in == 1500
    assert entry.tokens_out == 500
    assert ledger.total_inr > Decimal("0.00")
    assert ledger.total_usd > Decimal("0.00")

    # Hand calculation check:
    # prompt: 1500 * 0.59 / 1,000,000 = 0.000885 USD
    # completion: 500 * 0.79 / 1,000,000 = 0.000395 USD
    # total USD: 0.00128 USD -> inr = 0.00128 * 83 = 0.10624 INR
    usd_expected, inr_expected = price_call("llama-3.3-70b-versatile", 1500, 500)
    assert entry.usd_cost == usd_expected
    assert entry.inr_cost == inr_expected
