"""Image parser (Phase 1).

Performs OCR via :mod:`pytesseract` when available; otherwise records the
file as an unstructured asset so downstream agents know to schedule
follow-up vision work.
"""

from __future__ import annotations

import io
import logging

from app.ingestion.parsers.common.base import FileLike, ParsedDocument, ParserResult

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from PIL import Image  # type: ignore[import-not-found]
    import pytesseract  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    Image = None  # type: ignore[assignment]
    pytesseract = None  # type: ignore[assignment]


class ImageParser:
    name = "image"
    extensions = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp")

    async def parse(self, file: FileLike) -> ParserResult:
        data = await file.read()
        result = ParserResult()

        if Image is None or pytesseract is None:
            result.warnings.append(
                "Pillow/pytesseract not installed; skipping OCR for image assets"
            )
            result.chunks.append(
                ParsedDocument(
                    source=file.filename,
                    text="",
                    metadata={"parser": self.name, "ocr": False, "bytes": len(data)},
                )
            )
            return result

        try:
            image = Image.open(io.BytesIO(data))
            text = pytesseract.image_to_string(image)
        except Exception as exc:
            result.warnings.append(f"OCR failed for {file.filename}: {exc}")
            return result

        result.chunks.append(
            ParsedDocument(
                source=file.filename,
                text=text,
                metadata={
                    "parser": self.name,
                    "ocr": True,
                    "width": getattr(image, "width", None),
                    "height": getattr(image, "height", None),
                },
            )
        )
        return result
