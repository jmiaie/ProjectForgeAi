"""Hardened PDF parser (Phase 1 polish).

Capabilities (each with a graceful fallback when the underlying optional
dependency is missing):

* Per-page text extraction with width / height / rotation metadata.
* Long-page chunking via :mod:`app.ingestion.chunking` (sliding window with
  paragraph-aware breaks and configurable overlap).
* AcroForm field extraction (form-aware ingestion).
* Table extraction via ``pdfplumber`` when available — each table is emitted
  as a separate chunk so retrieval can cite the table directly.
* OCR fallback for scanned pages: if a page yields no extractable text we
  rasterise it (``pypdfium2`` -> ``Pillow``) and run ``pytesseract`` against
  the image.
"""

from __future__ import annotations

import io
import logging
from typing import Any

from app.ingestion.chunking import ChunkingOptions, chunk_text
from app.ingestion.parsers.common.base import (
    FileLike,
    ParsedDocument,
    ParserResult,
)

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional
    from pypdf import PdfReader  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    PdfReader = None  # type: ignore[assignment]

try:  # pragma: no cover - optional
    import pdfplumber  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    pdfplumber = None  # type: ignore[assignment]

try:  # pragma: no cover - optional
    import pypdfium2  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    pypdfium2 = None  # type: ignore[assignment]

try:  # pragma: no cover - optional
    import pytesseract  # type: ignore[import-not-found]
    from PIL import Image  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    pytesseract = None  # type: ignore[assignment]
    Image = None  # type: ignore[assignment]


class PDFParser:
    name = "pdf"
    extensions = (".pdf",)

    def __init__(
        self,
        chunking: ChunkingOptions | None = None,
        enable_tables: bool = True,
        enable_ocr_fallback: bool = True,
    ) -> None:
        self.chunking = chunking or ChunkingOptions()
        self.enable_tables = enable_tables
        self.enable_ocr_fallback = enable_ocr_fallback

    # ------------------------------------------------------------------
    async def parse(self, file: FileLike) -> ParserResult:
        data = await file.read()
        result = ParserResult()

        if PdfReader is None:
            return self._raw_text_fallback(file, data, result)

        try:
            reader = PdfReader(io.BytesIO(data))
        except Exception as exc:
            result.warnings.append(f"Could not open PDF {file.filename}: {exc}")
            return result

        total_pages = len(reader.pages)
        self._add_form_fields(file, reader, result)

        for index, page in enumerate(reader.pages):
            self._parse_page(file, data, page, index, total_pages, result)

        if self.enable_tables and pdfplumber is not None:
            self._extract_tables(file, data, total_pages, result)
        elif self.enable_tables and pdfplumber is None:
            result.warnings.append(
                "pdfplumber not installed; skipping table extraction"
            )

        return result

    # ------------------------------------------------------------------
    def _raw_text_fallback(
        self, file: FileLike, data: bytes, result: ParserResult
    ) -> ParserResult:
        result.warnings.append(
            "pypdf is not installed; falling back to raw text extraction"
        )
        text = data.decode("utf-8", errors="ignore")
        if text.strip():
            for fragment in chunk_text(text, self.chunking):
                result.chunks.append(
                    ParsedDocument(
                        source=file.filename,
                        text=fragment,
                        metadata={"parser": self.name, "fallback": True},
                    )
                )
        return result

    def _add_form_fields(
        self, file: FileLike, reader: Any, result: ParserResult
    ) -> None:
        try:
            fields = reader.get_form_text_fields() or {}
        except Exception as exc:  # pragma: no cover - defensive
            result.warnings.append(f"Form field extraction failed: {exc}")
            return
        if not fields:
            return
        rendered = "\n".join(
            f"{name}: {value}" for name, value in fields.items() if value
        )
        if not rendered.strip():
            return
        result.chunks.append(
            ParsedDocument(
                source=file.filename,
                text=rendered,
                metadata={
                    "parser": self.name,
                    "section": "form_fields",
                    "field_count": len(fields),
                    "fields": list(fields.keys()),
                },
            )
        )

    def _parse_page(
        self,
        file: FileLike,
        data: bytes,
        page: Any,
        index: int,
        total_pages: int,
        result: ParserResult,
    ) -> None:
        page_meta = self._page_dimensions(page)
        try:
            page_text = page.extract_text() or ""
        except Exception as exc:
            result.warnings.append(f"page {index} of {file.filename} failed: {exc}")
            page_text = ""

        if not page_text.strip() and self.enable_ocr_fallback:
            page_text = self._ocr_page(file, data, index, result, page_meta)
            if page_text:
                page_meta = {**page_meta, "ocr": True}

        if not page_text.strip():
            return

        fragments = chunk_text(page_text, self.chunking)
        for chunk_index, fragment in enumerate(fragments):
            metadata: dict[str, Any] = {
                "parser": self.name,
                "section": "page",
                "page": index + 1,
                "total_pages": total_pages,
                "chunk_index": chunk_index,
                "chunk_count": len(fragments),
                **page_meta,
            }
            result.chunks.append(
                ParsedDocument(
                    source=file.filename,
                    text=fragment,
                    metadata=metadata,
                )
            )

    def _page_dimensions(self, page: Any) -> dict[str, Any]:
        try:
            box = page.mediabox
            width = float(box.width)
            height = float(box.height)
        except Exception:  # pragma: no cover - defensive
            width = height = None  # type: ignore[assignment]
        rotation = 0
        try:
            rotation = int(page.rotation or 0)
        except Exception:  # pragma: no cover - defensive
            rotation = 0
        return {"width": width, "height": height, "rotation": rotation}

    def _ocr_page(
        self,
        file: FileLike,
        data: bytes,
        index: int,
        result: ParserResult,
        page_meta: dict[str, Any],
    ) -> str:
        if pypdfium2 is None or pytesseract is None or Image is None:
            result.warnings.append(
                f"page {index + 1} has no extractable text and OCR deps are unavailable"
            )
            return ""
        try:
            doc = pypdfium2.PdfDocument(data)
            page = doc[index]
            pil_image = page.render(scale=2).to_pil()
            text = pytesseract.image_to_string(pil_image)
            doc.close()
        except Exception as exc:  # pragma: no cover - defensive
            result.warnings.append(f"OCR fallback failed for page {index + 1}: {exc}")
            return ""
        return text or ""

    def _extract_tables(
        self,
        file: FileLike,
        data: bytes,
        total_pages: int,
        result: ParserResult,
    ) -> None:
        try:
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                for page_index, page in enumerate(pdf.pages):
                    try:
                        tables = page.extract_tables() or []
                    except Exception as exc:  # pragma: no cover - defensive
                        result.warnings.append(
                            f"Table extraction failed on page {page_index + 1}: {exc}"
                        )
                        continue
                    for table_index, rows in enumerate(tables):
                        rendered = self._render_table(rows)
                        if not rendered.strip():
                            continue
                        result.chunks.append(
                            ParsedDocument(
                                source=file.filename,
                                text=rendered,
                                metadata={
                                    "parser": self.name,
                                    "section": "table",
                                    "page": page_index + 1,
                                    "total_pages": total_pages,
                                    "table_index": table_index,
                                    "row_count": len(rows),
                                    "column_count": max(
                                        (len(row) for row in rows), default=0
                                    ),
                                },
                            )
                        )
        except Exception as exc:  # pragma: no cover - defensive
            result.warnings.append(f"pdfplumber failed: {exc}")

    @staticmethod
    def _render_table(rows: list[list[str | None]]) -> str:
        normalised = [
            [(cell or "").strip().replace("\n", " ") for cell in row] for row in rows
        ]
        return "\n".join(" | ".join(row) for row in normalised if any(row))
