import io
import tarfile
import zipfile
from pathlib import Path
from typing import BinaryIO

from ingestion.parsers.base import (
    ParsedChunk,
    ParsedDocument,
    normalize_text,
    read_bytes,
    source_hash,
    source_name_for,
)

CODE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".md",
    ".yaml",
    ".yml",
    ".json",
    ".sql",
    ".html",
    ".css",
    ".toml",
    ".rb",
    ".php",
    ".cs",
    ".kt",
    ".swift",
    ".vue",
    ".sh",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
}

MAX_FILE_BYTES = 256_000
MAX_FILES = 200


def parse_code_archive(
    source: str | Path | BinaryIO,
    *,
    filename: str | None = None,
) -> ParsedDocument:
    raw = read_bytes(source)
    source_name = source_name_for(source, filename, "codebase.zip")
    digest = source_hash(raw)
    warnings: list[str] = []
    chunks: list[ParsedChunk] = []

    lower_name = source_name.lower()
    if lower_name.endswith(".tar.gz") or lower_name.endswith(".tgz") or lower_name.endswith(".tar"):
        entries = _read_tar_entries(raw, lower_name.endswith(".gz") or lower_name.endswith(".tgz"))
    else:
        entries = _read_zip_entries(raw)

    indexed = 0
    for path, content in entries:
        suffix = Path(path).suffix.lower()
        if suffix not in CODE_EXTENSIONS:
            continue
        if len(content) > MAX_FILE_BYTES:
            warnings.append(f"{path}: skipped (> {MAX_FILE_BYTES} bytes)")
            continue
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            warnings.append(f"{path}: skipped (non-utf8)")
            continue

        normalized = normalize_text(text)
        if not normalized:
            continue

        indexed += 1
        chunks.append(
            ParsedChunk(
                source=f"{source_name}:{path}",
                text=normalized,
                metadata={
                    "parser": "codebase",
                    "source": source_name,
                    "source_hash": digest,
                    "file_path": path,
                    "file_type": suffix.removeprefix("."),
                    "chunk_index": indexed,
                },
            )
        )
        if indexed >= MAX_FILES:
            warnings.append(f"{source_name}: truncated after {MAX_FILES} files")
            break

    if not chunks:
        warnings.append(f"{source_name}: no indexable source files found in archive")

    return ParsedDocument(
        source=source_name,
        chunks=chunks,
        metadata={
            "parser": "codebase",
            "source": source_name,
            "source_hash": digest,
            "chunk_count": len(chunks),
            "archive_type": "tar" if "tar" in lower_name else "zip",
        },
        warnings=warnings,
    )


def _read_zip_entries(raw: bytes) -> list[tuple[str, bytes]]:
    entries: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            path = info.filename
            if path.startswith("__MACOSX/"):
                continue
            entries.append((path, archive.read(info)))
    return entries


def _read_tar_entries(raw: bytes, gzipped: bool) -> list[tuple[str, bytes]]:
    entries: list[tuple[str, bytes]] = []
    file_obj: BinaryIO = io.BytesIO(raw)
    mode = "r:gz" if gzipped else "r:"
    with tarfile.open(fileobj=file_obj, mode=mode) as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            path = member.name
            if path.startswith("._"):
                continue
            extracted = archive.extractfile(member)
            if extracted is None:
                continue
            entries.append((path, extracted.read()))
    return entries
