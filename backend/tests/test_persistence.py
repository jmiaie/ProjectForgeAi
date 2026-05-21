"""Tests covering the persistence layer (repositories + endpoints)."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from app.db.repositories import (
    AuditLogRepository,
    ConnectionRepository,
    ProjectRepository,
)
from app.db.session import get_session
from app.main import app
from app.security import decrypt_text, encrypt_text

SAMPLE_EMAIL = b"""From: alice@example.com
To: bob@example.com
Subject: Persistence test
Date: Wed, 01 Jan 2025 09:00:00 +0000
Content-Type: text/plain

Body for persistence test.
"""


def test_encrypt_roundtrip() -> None:
    cipher = encrypt_text("super secret token")
    assert cipher != "super secret token"
    assert decrypt_text(cipher) == "super secret token"


@pytest.mark.asyncio
async def test_project_repository_crud() -> None:
    async with get_session() as session:
        repo = ProjectRepository(session)
        project = await repo.create(
            project_id="proj_test_1",
            name="Repo Test",
            compliance="hipaa",
            objective="Validate persistence",
        )
        await session.commit()
        assert project.id == "proj_test_1"

        fetched = await repo.get("proj_test_1")
        assert fetched is not None
        assert fetched.compliance == "hipaa"

        await repo.update_status("proj_test_1", "orchestrated")
        await repo.merge_metadata("proj_test_1", {"region": "us-east"})
        await session.commit()

        fetched = await repo.get("proj_test_1")
        assert fetched is not None
        assert fetched.status == "orchestrated"
        assert fetched.project_metadata["region"] == "us-east"


@pytest.mark.asyncio
async def test_connection_repository_encrypts_secret() -> None:
    async with get_session() as session:
        repo = ConnectionRepository(session)
        record = await repo.create(
            connector_type="github",
            auth_kind="oauth",
            provider="github",
            project_id=None,
            scopes=["repo"],
            secret="ghp_xxxx",
        )
        await session.commit()
        assert record.encrypted_secret is not None
        assert record.encrypted_secret != "ghp_xxxx"
        assert decrypt_text(record.encrypted_secret) == "ghp_xxxx"


@pytest.mark.asyncio
async def test_audit_log_filtering() -> None:
    async with get_session() as session:
        audit = AuditLogRepository(session)
        await audit.record(action="filter.test", project_id=None, payload={"k": 1})
        await audit.record(action="filter.test", project_id=None, payload={"k": 2})
        await audit.record(action="other.action", project_id=None, payload={})
        await session.commit()

        only = await audit.list(action="filter.test", limit=50)
        assert len(only) >= 2
        assert all(entry.action == "filter.test" for entry in only)


def test_create_project_persists_and_lists() -> None:
    client = TestClient(app)
    files = [("files", ("kickoff.eml", io.BytesIO(SAMPLE_EMAIL), "message/rfc822"))]
    res = client.post(
        "/api/v1/projects/",
        files=files,
        data={"name": "Persistence Demo", "compliance": "standard"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    project_id = body["project_id"]

    res = client.get(f"/api/v1/projects/{project_id}")
    assert res.status_code == 200
    fetched = res.json()
    assert fetched["id"] == project_id
    assert fetched["name"] == "Persistence Demo"
    assert fetched["status"] == "orchestrated"

    res = client.get("/api/v1/projects/")
    assert res.status_code == 200
    listing = res.json()["items"]
    assert any(p["id"] == project_id for p in listing)


def test_intake_connection_persisted() -> None:
    client = TestClient(app)
    res = client.post(
        "/api/v1/intake/connections",
        json={
            "connector_type": "github",
            "auth_data": {"code": "abc123", "state": "xyz"},
        },
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["connection_id"].startswith("conn_")

    res = client.get("/api/v1/intake/connections")
    assert res.status_code == 200
    items = res.json()["items"]
    assert any(item["connector_type"] == "github" for item in items)


def test_audit_log_endpoint_returns_recent_events() -> None:
    client = TestClient(app)
    res = client.get("/api/v1/audit/", params={"limit": 50})
    assert res.status_code == 200
    actions = {entry["action"] for entry in res.json()["items"]}
    assert {"project.created", "project.ingested"}.issubset(actions)


def test_get_project_404() -> None:
    client = TestClient(app)
    res = client.get("/api/v1/projects/proj_does_not_exist")
    assert res.status_code == 404
