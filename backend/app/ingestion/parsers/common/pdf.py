"""PDF parser (Phase 1).

Uses :mod:`pypdf` when installed and falls back to a best-effort byte-level
text extractor so the pipeline never fails outright. Each PDF page becomes a
:class:`~app.ingestion.parsers.common.base.ParsedDocument` chunk so retrieval
can cite exact pages.
"""

from __future__ import annotations

import io
import logging
from typing import Any

from app.ingestion.parsers.common.base import FileLike, ParsedDocument, ParserResult

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from pypdf import PdfReader  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    PdfReader = None  # type: ignore[assignment]


class PDFParser:
    name = "pdf"
    extensions = (".pdf",)

    async def parse(self, file: FileLike) -> ParserResult:
        data = await file.read()
        result = ParserResult()

        if PdfReader is None:
            result.warnings.append(
                "pypdf is not installed; falling back to raw text extraction"
            )
            text = data.decode("utf-8", errors="ignore")
            if text.strip():
                result.chunks.append(
                    ParsedDocument(
                        source=file.filename,
                        text=text,
                        metadata={"parser": self.name, "fallback": True},
                    )
                )
            return result

        try:
            reader = PdfReader(io.BytesIO(data))
        except Exception as exc:
            result.warnings.append(f"Could not open PDF {file.filename}: {exc}")
            return result

        for page_index, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
            except Exception as exc:  # pragma: no cover - defensive
                result.warnings.append(
                    f"page {page_index} of {file.filename} failed: {exc}"
                )
                continue

            if not page_text.strip():
                continue

            metadata: dict[str, Any] = {
                "parser": self.name,
                "page": page_index + 1,
                "total_pages": len(reader.pages),
            }
            result.chunks.append(
                ParsedDocument(
                    source=file.filename,
                    text=page_text,
                    metadata=metadata,
                )
            )

        return result
