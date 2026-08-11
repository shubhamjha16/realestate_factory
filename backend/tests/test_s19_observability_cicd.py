"""
Sprint 19 Observability, PII Correlation & CI/CD Manifest Tests.

Verifies:
1. Rebuilding full multi-stage execution lifecycle from a single `job_id`.
2. PII log redaction correlation (`job_id`/`mandate_id`).
3. Integrity of CI/CD and deployment manifests (backend.yml, frontend.yml, render.yaml, vercel.json).
"""

from __future__ import annotations

import json
import os

from app.utils.observability import log_event, reconstruct_job_lifecycle


def test_job_id_reconstructs_full_lifecycle():
    """Verify passing a single job_id reconstructs full execution lifecycle timeline."""
    job_id = "job_obs_123"
    mandate_id = "mandate_obs_456"

    log_event(job_id=job_id, mandate_id=mandate_id, event_name="INGEST_COMPLETED", stage="ingest", payload={"count": 34})
    log_event(job_id=job_id, mandate_id=mandate_id, event_name="ADJUSTMENTS_COMPLETED", stage="adjustments", payload={"adjusted_rate": 7779})
    log_event(job_id=job_id, mandate_id=mandate_id, event_name="VALUATION_CONCLUDED", stage="reconciliation", payload={"concluded_value": 251042977})

    res = reconstruct_job_lifecycle(job_id)

    assert res["job_id"] == job_id
    assert res["mandate_id"] == mandate_id
    assert res["total_events"] >= 3
    assert any(e["event_name"] == "INGEST_COMPLETED" for e in res["lifecycle_stages"])


def test_observability_redacts_pii():
    """Verify owner names and GPS coordinates are redacted before logging."""
    record = log_event(
        job_id="job_pii_test",
        mandate_id="mandate_pii_test",
        event_name="PARSED_DOCUMENT",
        stage="ingest",
        payload={
            "owner": "Owner: Suresh Patel",
            "gps": "POINT(19.0760 72.8777)",
        },
    )

    assert "[REDACTED_OWNER]" in record["payload"]["owner"]
    assert "[REDACTED_COORDINATE]" in record["payload"]["gps"]


def test_cicd_manifests_exist_and_valid():
    """Verify CI/CD workflows and deployment infrastructure blueprints exist and are valid."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    backend_yml = os.path.join(root_dir, ".github", "workflows", "backend.yml")
    frontend_yml = os.path.join(root_dir, ".github", "workflows", "frontend.yml")
    render_yaml = os.path.join(root_dir, "render.yaml")
    vercel_json = os.path.join(root_dir, "vercel.json")

    assert os.path.exists(backend_yml)
    assert os.path.exists(frontend_yml)
    assert os.path.exists(render_yaml)
    assert os.path.exists(vercel_json)

    # Verify render.yaml contains alembic upgrade head pre-deploy command
    with open(render_yaml, encoding="utf-8") as f:
        render_content = f.read()
    assert "alembic upgrade head" in render_content

    # Verify vercel.json contains SPA rewrites
    with open(vercel_json, encoding="utf-8") as f:
        vercel_data = json.load(f)
    assert "rewrites" in vercel_data
