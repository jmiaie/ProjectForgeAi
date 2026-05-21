"""Integration smoke tests for the assembled API surface."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_health_and_openapi(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "healthy"

        docs = await client.get("/openapi.json")
        assert docs.status_code == 200
        paths = docs.json()["paths"]
        for route in (
            "/api/v1/projects/",
            "/api/v1/auth/login",
            "/api/v1/agents/orchestrate",
        ):
            assert route in paths


@pytest.mark.asyncio
async def test_cors_allows_browser_preflight(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/v1/projects/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code in {200, 204}
        assert response.headers.get("access-control-allow-origin")
