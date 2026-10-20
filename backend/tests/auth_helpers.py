"""Helpers for tests that call routes guarded by ``require_authenticated_user``."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app


def register_user(client: TestClient) -> dict:
    """Register a fresh user (with its default organisation) and return the body."""

    email = f"user_{uuid.uuid4().hex[:10]}@example.com"
    res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert res.status_code == 200, res.text
    return res.json()


def authed_client() -> TestClient:
    """Return a TestClient that sends a valid bearer token on every request."""

    client = TestClient(app)
    token = register_user(client)["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
