"""
No repository method is callable without a firm scope.

S5's exit proof asks for "a code review confirms no repository method is
callable without a firm scope". A code review confirms it once, for the code
that existed that day. This confirms it on every commit.

The rule: every public function in `app/repositories/` takes a `FirmScope`,
unless it appears in `UNSCOPED_BY_DESIGN` below with a reason. Adding a name to
that list is a deliberate act that shows up in review as exactly what it is.
"""

from __future__ import annotations

import inspect
import pkgutil
from importlib import import_module

import pytest

import app.repositories as repositories_pkg
from app.services.access.scope import FirmScope

# Each of these reads or writes without a caller's session, and each is here
# because there is no session to be had — not because scoping was inconvenient.
UNSCOPED_BY_DESIGN = {
    # The arq worker gets a job id off the queue. There is no user.
    "jobRepository.get_unscoped",
    # The worker owns this transition; it is a write to a known id, never a read
    # that could return another firm's row.
    "jobRepository.set_status",
    # Operational, scheduled, returns a count and no rows.
    "jobRepository.reconcile_orphans",
    # Sign-in: there is no scope until this succeeds.
    "userRepository.find_for_authentication",
    "userRepository.find_by_google_sub",
    # Builds the scope from a signed token's subject; cannot take what it makes.
    "userRepository.get_for_session",
    # Signup creates the first user of a firm, before any scope exists.
    "userRepository.create",
    "userRepository.save",
}


def _repository_functions():
    for info in pkgutil.iter_modules(repositories_pkg.__path__):
        module = import_module(f"app.repositories.{info.name}")
        for name, fn in vars(module).items():
            if name.startswith("_") or not inspect.isfunction(fn):
                continue
            if fn.__module__ != module.__name__:
                continue
            yield f"{info.name}.{name}", fn


def test_there_is_at_least_one_repository_to_check():
    """A guard that silently checks nothing is worse than no guard."""
    assert len(list(_repository_functions())) >= 15


@pytest.mark.parametrize("qualname,fn", list(_repository_functions()))
def test_every_repository_function_takes_a_firm_scope(qualname, fn):
    if qualname in UNSCOPED_BY_DESIGN:
        pytest.skip(f"{qualname} is unscoped by design")

    params = inspect.signature(fn).parameters
    assert "scope" in params, (
        f"{qualname} does not take a scope. Every repository function filters by "
        f"firm, or is listed in UNSCOPED_BY_DESIGN with a reason."
    )
    annotation = params["scope"].annotation
    assert annotation in (FirmScope, "FirmScope"), (
        f"{qualname}'s scope is annotated {annotation!r}, not FirmScope"
    )


@pytest.mark.parametrize("qualname,fn", list(_repository_functions()))
def test_the_scope_is_positional_and_early(qualname, fn):
    """
    Second parameter, after the session. Consistency is the point: a scope that
    is sometimes third and sometimes a keyword is a scope someone will forget.
    """
    if qualname in UNSCOPED_BY_DESIGN:
        pytest.skip(f"{qualname} is unscoped by design")

    names = list(inspect.signature(fn).parameters)
    assert names[:2] == ["db", "scope"], f"{qualname} takes {names[:2]}, expected ['db', 'scope']"


def test_every_exemption_still_exists():
    """A stale exemption is a hole that outlives the function it was written for."""
    actual = {q for q, _ in _repository_functions()}
    stale = UNSCOPED_BY_DESIGN - actual
    assert not stale, f"UNSCOPED_BY_DESIGN names functions that no longer exist: {stale}"


def test_routers_do_not_enforce_tenancy_themselves():
    """
    Tenancy is enforced at the repository layer, never the router. A router that
    filters by firm is a router someone will copy without the filter.
    """
    import pkgutil as _pkgutil

    import app.routers as routers_pkg

    for info in _pkgutil.iter_modules(routers_pkg.__path__):
        module = import_module(f"app.routers.{info.name}")
        source = inspect.getsource(module)
        assert "firm_id ==" not in source, f"{info.name} filters by firm in the router"
        assert "select(" not in source, f"{info.name} builds a query in the router"


def test_no_endpoint_accepts_a_firm_id_from_the_caller():
    """
    The scope comes from a signed token and nowhere else. An endpoint that reads
    a firm id from a header, a query parameter or a body is a way around all of
    the above.
    """
    from app.main import create_app

    spec = create_app().openapi()

    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            for param in op.get("parameters", []):
                assert "firm" not in param["name"].lower(), (
                    f"{method.upper()} {path} accepts {param['name']!r} from the caller"
                )

    # Only request schemas. A *response* may carry `firm_id` — telling a signed-in
    # user which firm they belong to is not a way in.
    request_schemas = {
        ref.rsplit("/", 1)[-1]
        for methods in spec["paths"].values()
        for op in methods.values()
        for content in (op.get("requestBody", {}).get("content") or {}).values()
        if (ref := content.get("schema", {}).get("$ref"))
    }
    assert request_schemas, "no request schemas found — the check would pass vacuously"

    # `firm_name` at signup is the name of a firm being created, not a way into
    # one that exists. What must never be accepted is a firm *identifier*.
    forbidden = {"firm_id", "firmid", "firm", "tenant_id", "tenantid", "org_id"}
    for name in request_schemas:
        for field in (spec["components"]["schemas"][name].get("properties") or {}):
            assert field.lower() not in forbidden, (
                f"request schema {name} accepts {field!r} from the caller; the firm "
                f"comes from the token and nowhere else"
            )
