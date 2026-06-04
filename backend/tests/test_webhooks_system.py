"""Tests for webhooks and system status APIs."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_webhook_404_for_missing_project(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/projects/proj_missing/webhooks/",
            json={"event": "issue.created", "data": {"id": "1"}},
        )
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_webhook_ingests_event(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCUS_ROOT", str(tmp_path / "locus"))
    monkeypatch.setenv("OMPA_VAULT_ROOT", str(tmp_path / "vaults"))

    from app.core.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create = await client.post(
            "/api/v1/projects/",
            data={"name": "Webhook Demo", "compliance": "standard"},
        )
        assert create.status_code == 200
        project_id = create.json()["project_id"]

        res = await client.post(
            f"/api/v1/projects/{project_id}/webhooks/",
            json={
                "event": "jira.issue.updated",
                "source": "jira",
                "data": {"key": "PROJ-1", "status": "In Progress"},
            },
        )
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "accepted"

        memory = await client.get(f"/api/v1/projects/{project_id}/memory/stats")
        assert memory.status_code == 200
        assert memory.json()["locus"]["total_chunks"] >= 1


@pytest.mark.asyncio
async def test_system_status_endpoint(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/system/status")
        assert res.status_code == 200
        body = res.json()
        assert body["status"] in {"healthy", "degraded", "unhealthy"}
        assert "checks" in body
        assert "database" in body["checks"]
