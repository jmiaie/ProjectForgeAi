"""Tests for /api/v1/forge endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_forge_validate_and_plan() -> None:
    client = TestClient(app)
    spec = {
        "projectName": "orders-api",
        "recipe": "express-api",
        "description": "Demo API",
        "port": 3000,
    }
    res = client.post("/api/v1/forge/validate", json=spec)
    assert res.status_code == 200, res.text
    assert res.json()["recipe"] == "express-api"

    res = client.post("/api/v1/forge/plan", json=spec)
    assert res.status_code == 200, res.text
    plan = res.json()
    assert plan["vars"]["projectName"] == "orders-api"
    assert plan["vars"]["port"] == "3000"


def test_forge_validate_rejects_bad_name() -> None:
    client = TestClient(app)
    res = client.post(
        "/api/v1/forge/validate",
        json={"projectName": "Bad", "recipe": "minimal"},
    )
    assert res.status_code == 422
