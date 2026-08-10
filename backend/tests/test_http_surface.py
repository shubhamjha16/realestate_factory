"""
The HTTP surface after the split.

S1 moved `api_bridge.py` into routers → controllers → services → repositories.
These assert the prototype's three routes still answer at their original paths,
and that the §5 `/api/v1` surface answers alongside them.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def test_health_answers_at_both_paths(client):
    for path in ("/health", "/api/v1/health"):
        r = client.get(path)
        assert r.status_code == 200, path
        assert r.json() == {"status": "ok", "service": "realestate-factory"}


def test_generate_rejects_empty_instructions_exactly_as_before(client):
    r = client.post("/generate", json={"instructions": "   "})
    assert r.status_code == 400
    assert r.json()["detail"] == "instructions required"


def test_unknown_job_returns_404(client):
    for path in ("/status/nope", "/api/v1/jobs/nope"):
        r = client.get(path)
        assert r.status_code == 404, path
        assert r.json()["detail"] == "Job not found"


def test_openapi_documents_the_legacy_alias_as_deprecated(client):
    spec = client.get("/openapi.json").json()
    assert spec["paths"]["/status/{job_id}"]["get"]["deprecated"] is True
    # §5: the alias stays mounted through S5, then returns 410.
    assert "/api/v1/jobs/{job_id}" in spec["paths"]


def test_no_route_handler_exceeds_fifteen_lines():
    """§7 S3's standard, held from S1 so it never has to be walked back."""
    import inspect

    from app.routers import generation, health, jobs

    for module in (generation, health, jobs):
        for name, fn in vars(module).items():
            if not callable(fn) or not getattr(fn, "__module__", "").startswith("app.routers"):
                continue
            body = inspect.getsource(fn).splitlines()
            assert len(body) <= 15, f"{module.__name__}.{name} is {len(body)} lines"
