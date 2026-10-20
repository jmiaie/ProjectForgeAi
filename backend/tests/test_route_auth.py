"""Unauthenticated callers get 401 on routes that touch tenant data or spend.

These routes only require *authentication* today. Organisation scoping
(which projects / audit rows / connections a user may see) is tracked as P0
in docs/ROADMAP.md.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.auth_helpers import authed_client

_SPEC = {"projectName": "auth-check", "recipe": "minimal"}

GUARDED_ROUTES: list[tuple[str, str, dict | None]] = [
    ("GET", "/api/v1/audit/", None),
    ("GET", "/api/v1/projects/", None),
    ("GET", "/api/v1/projects/proj_any", None),
    ("POST", "/api/v1/forge/runs", {"project_id": "proj_any", "spec": _SPEC}),
    ("GET", "/api/v1/forge/runs/run_any", None),
    ("GET", "/api/v1/forge/runs?project_id=proj_any", None),
    ("POST", "/api/v1/projects/proj_any/automations/", {"kind": "status_report"}),
    ("GET", "/api/v1/projects/proj_any/automations/", None),
    ("GET", "/api/v1/projects/proj_any/automations/auto_any", None),
    ("POST", "/api/v1/projects/proj_any/automations/auto_any/run-now", None),
    ("DELETE", "/api/v1/projects/proj_any/automations/auto_any", None),
    ("POST", "/api/v1/intake/connections", {"connector_type": "slack"}),
    ("GET", "/api/v1/intake/connections", None),
    (
        "POST",
        "/api/v1/agents/orchestrate",
        {"project_id": "proj_any", "objective": "spend tokens"},
    ),
]


@pytest.mark.parametrize(("method", "url", "body"), GUARDED_ROUTES)
def test_unauthenticated_request_gets_401(
    method: str, url: str, body: dict | None
) -> None:
    client = TestClient(app)
    res = client.request(method, url, json=body)
    assert res.status_code == 401, (method, url, res.text)
    assert res.headers.get("www-authenticate") == "Bearer"


@pytest.mark.parametrize(("method", "url", "body"), GUARDED_ROUTES)
def test_invalid_token_gets_401(method: str, url: str, body: dict | None) -> None:
    client = TestClient(app)
    res = client.request(
        method, url, json=body, headers={"Authorization": "Bearer not.a.jwt"}
    )
    assert res.status_code == 401, (method, url, res.text)


def test_authenticated_request_passes_the_auth_gate() -> None:
    client = authed_client()
    assert client.get("/api/v1/audit/").status_code == 200
    assert client.get("/api/v1/projects/").status_code == 200
    assert client.get("/api/v1/projects/proj_missing").status_code == 404


@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/automations/kinds",
        "/api/v1/agents/specialists",
        "/api/v1/intake/connectors",
    ],
)
def test_static_catalogue_routes_stay_public(url: str) -> None:
    assert TestClient(app).get(url).status_code == 200
