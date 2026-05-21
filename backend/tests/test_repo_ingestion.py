"""Tests for Phase 2 source-code repository archive ingestion."""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass

import pytest

from app.ingestion.parsers.code import RepoArchiveParser
from app.ingestion.pipeline import IngestionPipeline


@dataclass
class FakeUpload:
    filename: str
    payload: bytes

    async def read(self) -> bytes:
        return self.payload


def _build_repo_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "demo-repo/README.md",
            "# Demo Repo\n\nProjectForge ingestion sample.\n",
        )
        archive.writestr(
            "demo-repo/pyproject.toml",
            "[project]\nname = \"demo-repo\"\nversion = \"0.1.0\"\n",
        )
        archive.writestr(
            "demo-repo/src/main.py",
            "def main():\n    print('hello projectforge')\n",
        )
        archive.writestr(
            "demo-repo/node_modules/ignored/index.js",
            "module.exports = {}\n",
        )
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_repo_archive_parser_indexes_manifests_and_source() -> None:
    parser = RepoArchiveParser()
    result = await parser.parse(
        FakeUpload(filename="demo-repo.zip", payload=_build_repo_zip())
    )

    assert result.chunks
    summary = result.chunks[0]
    assert summary.metadata["section"] == "summary"
    assert summary.metadata["file_count"] == 3
    assert "demo-repo/README.md" in summary.metadata["readmes"]
    assert "demo-repo/pyproject.toml" in summary.metadata["manifests"]

    sections = {chunk.metadata.get("section") for chunk in result.chunks}
    assert "readme" in sections
    assert "manifest" in sections
    assert "source" in sections


@pytest.mark.asyncio
async def test_repo_archive_skips_vendor_directories() -> None:
    parser = RepoArchiveParser()
    result = await parser.parse(
        FakeUpload(filename="demo-repo.zip", payload=_build_repo_zip())
    )

    paths = [
        chunk.metadata.get("path")
        for chunk in result.chunks
        if chunk.metadata.get("path")
    ]
    assert not any("node_modules" in path for path in paths)


@pytest.mark.asyncio
async def test_pipeline_routes_repo_zip(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCUS_ROOT", str(tmp_path / "locus"))
    monkeypatch.setenv("OMPA_VAULT_ROOT", str(tmp_path / "vaults"))

    from app.core.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]

    pipeline = IngestionPipeline()
    summary = await pipeline.process_files(
        project_id="repo-demo",
        files=[FakeUpload(filename="demo-repo.zip", payload=_build_repo_zip())],
    )

    assert summary["status"] == "ingested"
    assert summary["files"][0]["parser"] == "repo_archive"
    assert summary["total_chunks"] >= 3
