"""Integration test for the project creation endpoint."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient

from app.main import app

SAMPLE_EMAIL = b"""From: alice@example.com
To: bob@example.com
Subject: Kickoff
Date: Wed, 01 Jan 2025 09:00:00 +0000
Content-Type: text/plain

Project kickoff payload.
"""


def test_create_project_with_email_upload() -> None:
    client = TestClient(app)
    files = [("files", ("kickoff.eml", io.BytesIO(SAMPLE_EMAIL), "message/rfc822"))]
    res = client.post(
        "/api/v1/projects/",
        files=files,
        data={"compliance": "standard"},
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["status"] == "orchestrated"
    assert payload["project_id"].startswith("proj_")
    assert payload["ingestion"]["total_files"] == 1
    assert payload["ingestion"]["files"][0]["parser"] == "email"
    assert payload["plan"] is None
    assert isinstance(payload["recommended_connectors"], list)
