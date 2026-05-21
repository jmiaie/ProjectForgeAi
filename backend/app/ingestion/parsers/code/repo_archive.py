"""Source-code repository archive parser (Phase 2).

Ingests zipped or tarred repository snapshots uploaded during project
intake. Builds a searchable inventory (languages, manifests, tree summary)
and chunks high-signal files such as READMEs, dependency manifests, and a
bounded sample of source files.
"""

from __future__ import annotations

import io
import logging
import os
import tarfile
import zipfile
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from app.ingestion.chunking import ChunkingOptions, chunk_text
from app.ingestion.parsers.common.base import (
    FileLike,
    ParsedDocument,
    ParserResult,
)

logger = logging.getLogger(__name__)

EXTENSIONS = (".zip", ".tar", ".tar.gz", ".tgz")

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    "target",
}

MANIFEST_NAMES = {
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pyproject.toml",
    "requirements.txt",
    "Pipfile",
    "poetry.lock",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "Gemfile",
    "composer.json",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "Makefile",
    "justfile",
}

README_NAMES = {"readme.md", "readme", "readme.txt", "readme.rst"}

SOURCE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".rb",
    ".cs",
    ".cpp",
    ".c",
    ".h",
    ".swift",
    ".kt",
    ".scala",
    ".sql",
    ".sh",
    ".yaml",
    ".yml",
    ".toml",
    ".md",
}

MAX_READ_BYTES = 50_000
MAX_CONTENT_FILES = 40


@dataclass(frozen=True)
class ArchiveMember:
    path: str
    size: int
    data: bytes | None = None


class RepoArchiveParser:
    name = "repo_archive"
    extensions = EXTENSIONS

    def __init__(self, chunking: ChunkingOptions | None = None) -> None:
        self.chunking = chunking or ChunkingOptions()

    async def parse(self, file: FileLike) -> ParserResult:
        data = await file.read()
        result = ParserResult()

        try:
            members = list(self._extract_members(file.filename, data))
        except Exception as exc:
            result.warnings.append(f"Could not open archive {file.filename}: {exc}")
            return result

        if not members:
            result.warnings.append(f"Archive {file.filename} contained no files")
            return result

        language_counts = Counter()
        manifest_paths: list[str] = []
        readme_paths: list[str] = []
        source_candidates: list[ArchiveMember] = []

        for member in members:
            basename = os.path.basename(member.path)
            ext = os.path.splitext(basename)[1].lower()
            if ext:
                language_counts[ext] += 1
            lower_name = basename.lower()
            if lower_name in README_NAMES:
                readme_paths.append(member.path)
            elif basename in MANIFEST_NAMES:
                manifest_paths.append(member.path)
            elif ext in SOURCE_EXTENSIONS and member.data is not None:
                source_candidates.append(member)

        tree_lines = self._tree_summary(members)
        summary_lines = [
            f"Repository archive: {file.filename}",
            f"Files indexed: {len(members)}",
        ]
        if language_counts:
            top_langs = language_counts.most_common(10)
            summary_lines.append(
                "Extension breakdown: "
                + ", ".join(f"{ext or '(no ext)'}={count}" for ext, count in top_langs)
            )
        if manifest_paths:
            summary_lines.append("Manifests: " + ", ".join(sorted(manifest_paths)[:20]))
        if readme_paths:
            summary_lines.append("README files: " + ", ".join(sorted(readme_paths)))

        result.chunks.append(
            ParsedDocument(
                source=file.filename,
                text="\n".join(summary_lines) + "\n\n" + "\n".join(tree_lines[:80]),
                metadata={
                    "parser": self.name,
                    "section": "summary",
                    "format": "repo_archive",
                    "file_count": len(members),
                    "language_counts": dict(language_counts),
                    "manifests": manifest_paths,
                    "readmes": readme_paths,
                },
            )
        )

        content_targets = self._select_content_targets(
            manifest_paths, readme_paths, source_candidates, members
        )
        for path in content_targets[:MAX_CONTENT_FILES]:
            member = next((m for m in members if m.path == path), None)
            if member is None or member.data is None:
                continue
            text = self._decode_text(member.data)
            if not text.strip():
                continue
            section = self._section_for_path(path)
            for index, piece in enumerate(chunk_text(text, self.chunking)):
                result.chunks.append(
                    ParsedDocument(
                        source=file.filename,
                        text=piece,
                        metadata={
                            "parser": self.name,
                            "section": section,
                            "format": "repo_archive",
                            "path": path,
                            "chunk_index": index,
                        },
                    )
                )

        return result

    def _extract_members(self, filename: str, data: bytes) -> Iterable[ArchiveMember]:
        lower = filename.lower()
        if lower.endswith(".zip"):
            yield from self._extract_zip(data)
        elif lower.endswith((".tar", ".tar.gz", ".tgz")):
            yield from self._extract_tar(data)
        else:
            raise ValueError(f"Unsupported archive extension for {filename}")

    def _extract_zip(self, data: bytes) -> Iterable[ArchiveMember]:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                normalized = self._normalize_path(info.filename)
                if normalized is None:
                    continue
                raw = archive.read(info)
                yield ArchiveMember(
                    path=normalized,
                    size=len(raw),
                    data=raw if len(raw) <= MAX_READ_BYTES else None,
                )

    def _extract_tar(self, data: bytes) -> Iterable[ArchiveMember]:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                normalized = self._normalize_path(member.name)
                if normalized is None:
                    continue
                extracted = archive.extractfile(member)
                if extracted is None:
                    continue
                raw = extracted.read()
                yield ArchiveMember(
                    path=normalized,
                    size=len(raw),
                    data=raw if len(raw) <= MAX_READ_BYTES else None,
                )

    def _normalize_path(self, path: str) -> str | None:
        cleaned = path.replace("\\", "/").lstrip("./")
        parts = [part for part in cleaned.split("/") if part and part != "."]
        if any(part in SKIP_DIRS for part in parts):
            return None
        if parts and parts[0].endswith(".git"):
            return None
        return "/".join(parts)

    def _tree_summary(self, members: list[ArchiveMember]) -> list[str]:
        paths = sorted({member.path for member in members})
        lines: list[str] = ["File tree (top entries):"]
        seen_prefixes: set[str] = set()
        for path in paths[:120]:
            parts = path.split("/")
            for depth in range(1, min(len(parts), 4) + 1):
                prefix = "/".join(parts[:depth])
                if prefix in seen_prefixes:
                    continue
                seen_prefixes.add(prefix)
                indent = "  " * (depth - 1)
                label = parts[depth - 1]
                suffix = "/" if depth < len(parts) else ""
                lines.append(f"{indent}{label}{suffix}")
        return lines

    def _select_content_targets(
        self,
        manifest_paths: list[str],
        readme_paths: list[str],
        source_candidates: list[ArchiveMember],
        members: list[ArchiveMember],
    ) -> list[str]:
        selected: list[str] = []
        selected.extend(sorted(set(readme_paths)))
        selected.extend(sorted(set(manifest_paths)))
        for member in sorted(source_candidates, key=lambda m: (m.path.count("/"), m.path)):
            if member.path not in selected:
                selected.append(member.path)
        return selected

    def _section_for_path(self, path: str) -> str:
        basename = os.path.basename(path)
        if basename.lower() in README_NAMES:
            return "readme"
        if basename in MANIFEST_NAMES:
            return "manifest"
        return "source"

    def _decode_text(self, data: bytes) -> str:
        for encoding in ("utf-8", "latin-1"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")
