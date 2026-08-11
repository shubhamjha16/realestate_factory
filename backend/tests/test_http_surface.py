"""
The HTTP surface.

Everything here is answerable without a database: validation runs before the
handler, and health and the spec touch no store. Anything that needs a row lives
in `test_job_repository.py`, which skips without a live Postgres.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.configs.jobTypes import ALL_JOB_TYPES_SORTED
from app.main import create_app
from app.routers.deps import current_scope
from app.services.access.scope import FirmScope

SCOPE = FirmScope(
    firm_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
    user_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
    role="analyst",
)


@pytest.fixture(scope="module")
def client():
    """
    Signed in as an analyst, with no database.

    The scope is overridden rather than minted, because what these tests are
    about is validation and shape. That the scope itself can only come from a
    signed token is `test_repository_scope_guard.py`'s job, and that an absent
    token is refused is `test_requires_authentication` below.
    """
    app = create_app()
    app.dependency_overrides[current_scope] = lambda: SCOPE
    return TestClient(app)


def test_every_route_but_health_and_auth_requires_a_session():
    """No token, no data. The legacy unprefixed alias included."""
    anonymous = TestClient(create_app())
    for method, path in (
        ("post", "/generate"),
        ("get", "/jobs/11111111-1111-1111-1111-111111111111"),
        ("get", "/status/11111111-1111-1111-1111-111111111111"),
        ("get", "/api/v1/jobs"),
        ("get", "/api/v1/clients"),
        ("get", "/api/v1/mandates"),
        ("get", "/api/v1/auth/me"),
    ):
        r = (
            anonymous.post(path, json={})
            if method == "post"
            else anonymous.get(path)
        )
        assert r.status_code == 401, f"{method.upper()} {path} answered {r.status_code}"


def test_health_answers_at_both_paths(client):
    for path in ("/health", "/api/v1/health"):
        r = client.get(path)
        assert r.status_code == 200, path
        assert r.json() == {"status": "ok", "service": "realestate-factory"}


def test_openapi_documents_the_legacy_alias_as_deprecated(client):
    spec = client.get("/openapi.json").json()
    assert spec["paths"]["/status/{job_id}"]["get"]["deprecated"] is True
    # §5: the alias stays mounted through S5, then returns 410.
    assert "/api/v1/jobs/{job_id}" in spec["paths"]


def test_the_spec_is_complete_enough_for_type_generation(client):
    """
    §3's whole reason for one repository: the console's types are generated from
    this spec. A response with no schema generates as `unknown` and the gate
    stops catching anything.
    """
    spec = client.get("/openapi.json").json()
    assert "JobStatus" in spec["components"]["schemas"]
    assert "GenerateRequest" in spec["components"]["schemas"]

    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            ok = next(
                (op["responses"][code] for code in ("200", "201", "202") if code in op["responses"]),
                None,
            )
            assert ok, f"{method.upper()} {path} documents no success response"
            if path.endswith("/health"):
                continue
            assert ok["content"]["application/json"]["schema"], f"{method.upper()} {path}"


# ── validation: a 422 that names the field ────────────────────────────────────


def test_unknown_job_type_is_422_naming_the_field_and_listing_valid_values(client):
    r = client.post("/generate", json={"instructions": "value this flat", "job_type": "bank_valuation"})
    assert r.status_code == 422

    detail = r.json()["detail"]
    assert any("job_type" in err["loc"] for err in detail)
    message = str(detail)
    for job_type in ALL_JOB_TYPES_SORTED:
        assert job_type in message, f"{job_type} missing from the 422"


def test_a_valuation_without_a_basis_is_refused_rather_than_defaulted(client):
    r = client.post("/generate", json={"instructions": "value this flat", "job_type": "valuation_report"})
    assert r.status_code == 422

    message = str(r.json()["detail"])
    assert "basis" in message and "purpose" in message
    # The point is that it is refused, not that it silently became market value.
    assert "market" not in message.split("basis")[0]


def test_a_valuation_with_a_basis_and_purpose_is_accepted(monkeypatch):
    """
    The positive case. The store and the graph are stubbed — what is under test
    is that a fully-stated valuation request gets past validation and is
    accepted as a job, not what the graph then does with it.
    """
    import uuid as _uuid

    from app.configs.dbConfig import get_db
    from app.models.job import Job
    from app.repositories import jobRepository
    from app.services import generationService

    async def _fake_create(_db, _scope, **kwargs):
        return Job(
            id=_uuid.uuid4(),
            status="queued",
            job_type=kwargs.get("job_type", ""),
            instructions=kwargs.get("instructions", ""),
            doc_url="",
            error="",
        )

    async def _no_existing(_db, _scope, _key):
        return None

    async def _fake_enqueue(*_a, **_k):
        return "queued"

    monkeypatch.setattr(jobRepository, "create", _fake_create)
    monkeypatch.setattr(jobRepository, "find_by_idempotency_key", _no_existing)
    monkeypatch.setattr(generationService, "enqueue", _fake_enqueue)

    app = create_app()
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[current_scope] = lambda: SCOPE

    r = TestClient(app).post(
        "/generate",
        json={
            "instructions": "value this flat",
            "job_type": "valuation_report",
            "basis": "liquidation",
            "purpose": "ibc",
        },
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "queued"
    assert body["job_type"] == "valuation_report"
    assert _uuid.UUID(body["job_id"])
    # Not finished, so not frozen — the repository still accepts status writes.
    assert body["terminal_at"] is None


def test_empty_instructions_are_refused(client):
    r = client.post("/generate", json={"instructions": "   "})
    assert r.status_code == 422
    assert "instructions required" in str(r.json()["detail"])


def test_an_oversized_property_data_payload_is_refused(client):
    from app.validators.generateValidator import MAX_PROPERTY_DATA_CHARS

    r = client.post(
        "/generate",
        json={"instructions": "x", "property_data": "a" * (MAX_PROPERTY_DATA_CHARS + 1)},
    )
    assert r.status_code == 422
    assert any("property_data" in err["loc"] for err in r.json()["detail"])


# ── layering ──────────────────────────────────────────────────────────────────


def test_no_route_handler_exceeds_fifteen_lines_or_touches_sql():
    """§7 S3's standard: routers hold no logic and no store access."""
    import inspect

    from app.routers import generation, health, jobs

    for module in (generation, health, jobs):
        source = inspect.getsource(module)
        for forbidden in ("select(", "session.execute", "sqlalchemy.select", "text("):
            assert forbidden not in source, f"{module.__name__} contains SQL: {forbidden}"

        for name, fn in vars(module).items():
            # Defined here, not imported — `current_scope` lives in routers/deps
            # and is a dependency, not a handler.
            if not callable(fn) or getattr(fn, "__module__", None) != module.__name__:
                continue
            body = inspect.getsource(fn).splitlines()
            assert len(body) <= 15, f"{module.__name__}.{name} is {len(body)} lines"
