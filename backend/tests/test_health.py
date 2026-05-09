"""Smoke tests covering the FastAPI app and intake wizard wiring."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    payload = res.json()
    assert payload["status"] == "healthy"
    assert "version" in payload
    assert "llm_default" in payload


def test_intake_connectors_endpoint() -> None:
    client = TestClient(app)
    res = client.get("/api/v1/intake/connectors", params={"compliance": "standard"})
    assert res.status_code == 200
    payload = res.json()
    assert payload["compliance"] == "standard"
    assert isinstance(payload["recommended"], list)
    names = {c["name"] for c in payload["recommended"]}
    assert {"google", "slack", "github", "mcp_server"}.issubset(names)


def test_intake_connection_post_oauth_stub() -> None:
    client = TestClient(app)
    res = client.post(
        "/api/v1/intake/connections",
        json={
            "connector_type": "google",
            "auth_data": {"code": "abc123", "state": "xyz"},
            "project_id": "demo",
        },
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["status"] == "connected"
    assert payload["connector"] == "google"


def test_intake_connection_unknown_connector() -> None:
    client = TestClient(app)
    res = client.post(
        "/api/v1/intake/connections",
        json={"connector_type": "totally_made_up", "auth_data": {}},
    )
    assert res.status_code == 400
