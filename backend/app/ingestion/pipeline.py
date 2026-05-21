"""End-to-end ingestion pipeline.

The pipeline routes each uploaded file to the appropriate parser (Phase 1
common formats + Phase 2 CAD/BIM + source repo archives), indexes the
resulting chunks in Locus, and records a corresponding decision trail entry
in OMPA.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable

from app.ingestion.parsers.cad import DXFParser, IFCParser
from app.ingestion.parsers.code import RepoArchiveParser
from app.ingestion.parsers.common import (
    EmailParser,
    ImageParser,
    PDFParser,
)
from app.ingestion.parsers.common.base import FileLike, ParserResult
from app.storage.locus_adapter import LocusAdapter
from app.storage.ompa_adapter import OmpaAdapter


class IngestionPipeline:
    """Coordinates parsing + indexing + memory recording."""

    def __init__(self) -> None:
        self.parsers = [
            PDFParser(),
            ImageParser(),
            EmailParser(),
            DXFParser(),
            IFCParser(),
            RepoArchiveParser(),
        ]

    def _matches_extension(self, filename: str, extensions: tuple[str, ...]) -> bool:
        lower = filename.lower()
        for ext in sorted(extensions, key=len, reverse=True):
            if lower.endswith(ext):
                return True
        return False

    def _select_parser(self, filename: str):
        for parser in self.parsers:
            if self._matches_extension(filename, parser.extensions):
                return parser
        return None

    async def process_files(
        self, project_id: str, files: Iterable[FileLike]
    ) -> dict[str, Any]:
        locus = LocusAdapter(project_id)
        ompa = OmpaAdapter(project_id)
        await ompa.session_start()

        per_file: list[dict[str, Any]] = []
        all_chunks: list[dict[str, Any]] = []
        warnings: list[str] = []

        for file in files:
            parser = self._select_parser(file.filename)
            if parser is None:
                warnings.append(f"No parser registered for {file.filename}")
                per_file.append(
                    {"file": file.filename, "parser": None, "chunks": 0}
                )
                continue

            result: ParserResult = await parser.parse(file)
            warnings.extend(result.warnings)
            chunk_dicts = [asdict(chunk) for chunk in result.chunks]
            all_chunks.extend(chunk_dicts)
            per_file.append(
                {
                    "file": file.filename,
                    "parser": parser.name,
                    "chunks": len(chunk_dicts),
                    "warnings": result.warnings,
                }
            )
            await ompa.record_decision(
                f"Parsed {file.filename} with {parser.name} producing {len(chunk_dicts)} chunks"
            )

        if all_chunks:
            await locus.index_files(all_chunks)

        return {
            "status": "ingested",
            "project_id": project_id,
            "total_files": len(per_file),
            "total_chunks": len(all_chunks),
            "files": per_file,
            "warnings": warnings,
        }
