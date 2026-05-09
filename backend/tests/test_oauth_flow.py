"""Tests for the real OAuth 2.0 / PKCE flow."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.models import OAuthState
from app.db.session import get_session
from app.integrations.oauth.flow import OAuthFlow, OAuthFlowError
from app.integrations.oauth.pkce import generate_pkce_pair, make_state
from app.integrations.oauth.providers import get_provider_metadata
from app.main import app
from app.security import decrypt_text


# -----------------------------------------------------------------------------
# Configure provider creds for the test session
# -----------------------------------------------------------------------------
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-google-secret")
os.environ.setdefault("GITHUB_CLIENT_ID", "test-github-id")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "test-github-secret")
os.environ.setdefault("OAUTH_REDIRECT_BASE_URL", "http://localhost:8000")
get_settings.cache_clear()  # type: ignore[attr-defined]


# -----------------------------------------------------------------------------
# PKCE primitives
# -----------------------------------------------------------------------------
def test_pkce_pair_is_rfc7636_compliant() -> None:
    pair = generate_pkce_pair()
    assert 43 <= len(pair.code_verifier) <= 128
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(pair.code_verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    assert pair.code_challenge == expected
    assert pair.method == "S256"


def test_state_token_is_unique() -> None:
    states = {make_state() for _ in range(50)}
    assert len(states) == 50


# -----------------------------------------------------------------------------
# Authorize URL
# -----------------------------------------------------------------------------
def test_authorize_endpoint_returns_url_with_pkce() -> None:
    client = TestClient(app)
    res = client.get(
        "/api/v1/intake/oauth/google/authorize",
        params={"project_id": "p_oauth_test"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    parsed = urlparse(body["authorize_url"])
    qs = parse_qs(parsed.query)
    assert qs["client_id"] == ["test-google-id"]
    assert qs["response_type"] == ["code"]
    assert qs["state"] == [body["state"]]
    assert qs["code_challenge_method"] == ["S256"]
    assert "code_challenge" in qs
    assert qs["redirect_uri"] == [
        "http://localhost:8000/api/v1/intake/oauth/google/callback"
    ]


def test_authorize_endpoint_404_for_unknown_provider() -> None:
    client = TestClient(app)
    res = client.get("/api/v1/intake/oauth/totally-fake/authorize")
    assert res.status_code == 404


def test_authorize_endpoint_400_when_provider_unconfigured() -> None:
    if os.environ.get("MICROSOFT_CLIENT_ID"):
        pytest.skip("MICROSOFT_CLIENT_ID is set in this environment")
    client = TestClient(app)
    res = client.get("/api/v1/intake/oauth/microsoft/authorize")
    assert res.status_code == 400
    assert "not configured" in res.json()["detail"].lower()


# -----------------------------------------------------------------------------
# Callback / token exchange
# -----------------------------------------------------------------------------
class _FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeHttpxClient:
    def __init__(self, response: _FakeResponse) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    async def post(self, url: str, data: dict[str, Any], headers: dict[str, str]) -> _FakeResponse:
        self.calls.append({"url": url, "data": data, "headers": headers})
        return self.response


@pytest.mark.asyncio
async def test_consume_state_rejects_unknown_value() -> None:
    async with get_session() as session:
        flow = OAuthFlow(session)
        with pytest.raises(OAuthFlowError):
            await flow.consume_state("does-not-exist")


@pytest.mark.asyncio
async def test_full_callback_persists_encrypted_token(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_response = _FakeResponse(
        200,
        {
            "access_token": "ya29.fake-access",
            "refresh_token": "1//fake-refresh",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "email profile",
        },
    )
    fake_client = _FakeHttpxClient(fake_response)

    async def fake_post(self: OAuthFlow, token_url: str, payload: dict[str, str]) -> dict[str, Any]:
        fake_client.calls.append({"url": token_url, "data": payload})
        assert payload["grant_type"] == "authorization_code"
        assert payload["code_verifier"], "PKCE verifier should be sent"
        return fake_response.json()

    monkeypatch.setattr(OAuthFlow, "_post_token_exchange", fake_post)

    client = TestClient(app)

    auth_res = client.get(
        "/api/v1/intake/oauth/google/authorize",
        params={"project_id": "p_oauth_callback"},
    )
    assert auth_res.status_code == 200
    state = auth_res.json()["state"]

    cb_res = client.get(
        "/api/v1/intake/oauth/google/callback",
        params={"code": "fake-code", "state": state},
    )
    assert cb_res.status_code == 200, cb_res.text
    body = cb_res.json()
    assert body["status"] == "connected"
    assert body["provider"] == "google"
    connection_id = body["connection_id"]

    list_res = client.get(
        "/api/v1/intake/connections",
        params={"project_id": "p_oauth_callback"},
    )
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    matching = [c for c in items if c["id"] == connection_id]
    assert matching, "newly-stored connection should be listed"

    audit_res = client.get(
        "/api/v1/audit/", params={"project_id": "p_oauth_callback"}
    )
    actions = {entry["action"] for entry in audit_res.json()["items"]}
    assert {"oauth.authorize_started", "oauth.connected"}.issubset(actions)

    async with get_session() as session:
        from sqlalchemy import select

        from app.db.models import Connection

        result = await session.execute(
            select(Connection).where(Connection.id == connection_id)
        )
        conn = result.scalar_one()
        assert conn.encrypted_secret is not None
        decrypted = json.loads(decrypt_text(conn.encrypted_secret))
        assert decrypted["access_token"] == "ya29.fake-access"
        assert decrypted["refresh_token"] == "1//fake-refresh"

        result = await session.execute(
            select(OAuthState).where(OAuthState.state == state)
        )
        assert result.scalar_one_or_none() is None, "state row should be consumed"


def test_callback_rejects_unknown_state() -> None:
    client = TestClient(app)
    res = client.get(
        "/api/v1/intake/oauth/google/callback",
        params={"code": "x", "state": "definitely-not-a-real-state"},
    )
    assert res.status_code == 400


def test_oauth_providers_endpoint() -> None:
    client = TestClient(app)
    res = client.get("/api/v1/intake/oauth/providers")
    assert res.status_code == 200
    names = {p["name"] for p in res.json()["providers"]}
    assert {"google", "microsoft", "github", "slack"}.issubset(names)


def test_provider_metadata_lookup_raises_on_unknown() -> None:
    with pytest.raises(ValueError):
        get_provider_metadata("not-a-provider")
