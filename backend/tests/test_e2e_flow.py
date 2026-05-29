"""End-to-end API flow: create project → graph → memory retrieval."""

from __future__ import annotations

import io

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app

SAMPLE_EMAIL = b"""From: alice@example.com
To: bob@example.com
Subject: Kickoff
Date: Wed, 01 Jan 2025 09:00:00 +0000
Content-Type: text/plain

Hello Bob,

ProjectForge kickoff notes for the Riverside build.

Cheers,
Alice
"""


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCUS_ROOT", str(tmp_path / "locus"))
    monkeypatch.setenv("OMPA_VAULT_ROOT", str(tmp_path / "vaults"))
    monkeypatch.setenv("GRAPH_DATA_ROOT", str(tmp_path / "graph"))
    from app.core.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]
    return create_app()


@pytest.mark.asyncio
async def test_project_intake_graph_and_memory_e2e(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCUS_ROOT", str(tmp_path / "locus2"))
    monkeypatch.setenv("OMPA_VAULT_ROOT", str(tmp_path / "vaults2"))
    monkeypatch.setenv("GRAPH_DATA_ROOT", str(tmp_path / "graph2"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"files": ("kickoff.eml", io.BytesIO(SAMPLE_EMAIL), "message/rfc822")}
        data = {
            "name": "E2E Riverside",
            "compliance": "standard",
            "objective": "Draft kickoff schedule and identify risks",
        }
        created = await client.post("/api/v1/projects/", data=data, files=files)
        assert created.status_code == 200, created.text
        payload = created.json()
        project_id = payload["project_id"]
        assert payload["ingestion"]["total_chunks"] >= 1
        assert payload.get("plan") is not None

        project = await client.get(f"/api/v1/projects/{project_id}")
        assert project.status_code == 200
        assert project.json()["name"] == "E2E Riverside"

        graph_stats = await client.get(f"/api/v1/projects/{project_id}/graph/stats")
        assert graph_stats.status_code == 200
        stats = graph_stats.json()
        assert stats["total_nodes"] >= 1

        react_flow = await client.get(
            f"/api/v1/projects/{project_id}/graph/react-flow"
        )
        assert react_flow.status_code == 200
        assert "nodes" in react_flow.json()

        memory_stats = await client.get(f"/api/v1/projects/{project_id}/memory/stats")
        assert memory_stats.status_code == 200
        assert memory_stats.json()["locus"]["total_chunks"] >= 1

        retrieval = await client.post(
            f"/api/v1/projects/{project_id}/memory/retrieve",
            json={"query": "kickoff Riverside", "limit": 5},
        )
        assert retrieval.status_code == 200
        assert retrieval.json()["result_count"] >= 1

        listed = await client.get("/api/v1/projects/")
        assert listed.status_code == 200
        ids = {item["id"] for item in listed.json()["items"]}
        assert project_id in ids
