"""Tests for the ingestion pipeline & Phase 1 parsers."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.ingestion.parsers.common import EmailParser
from app.ingestion.pipeline import IngestionPipeline


@dataclass
class FakeUpload:
    filename: str
    payload: bytes

    async def read(self) -> bytes:
        return self.payload


SAMPLE_EMAIL = b"""From: alice@example.com
To: bob@example.com
Subject: Kickoff
Date: Wed, 01 Jan 2025 09:00:00 +0000
Content-Type: text/plain

Hello Bob,

Looking forward to the project.

Cheers,
Alice
"""


@pytest.mark.asyncio
async def test_email_parser_splits_headers_and_body() -> None:
    parser = EmailParser()
    upload = FakeUpload(filename="kickoff.eml", payload=SAMPLE_EMAIL)
    result = await parser.parse(upload)

    sections = {chunk.metadata.get("section") for chunk in result.chunks}
    assert "headers" in sections
    assert "body" in sections


@pytest.mark.asyncio
async def test_pipeline_routes_files_to_parsers(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCUS_ROOT", str(tmp_path / "locus"))
    monkeypatch.setenv("OMPA_VAULT_ROOT", str(tmp_path / "vaults"))

    from app.core.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]

    pipeline = IngestionPipeline()
    summary = await pipeline.process_files(
        project_id="demo",
        files=[FakeUpload(filename="kickoff.eml", payload=SAMPLE_EMAIL)],
    )

    assert summary["status"] == "ingested"
    assert summary["total_files"] == 1
    assert summary["total_chunks"] >= 1
    assert summary["files"][0]["parser"] == "email"
