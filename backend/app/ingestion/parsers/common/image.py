import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from ingestion.parsers.base import (
    ParsedChunk,
    ParsedDocument,
    chunk_text,
    normalize_text,
    read_bytes,
    source_hash,
    source_name_for,
)
from core.config import settings


def _tesseract_available() -> bool:
    if settings.TESSERACT_CMD:
        return Path(settings.TESSERACT_CMD).exists()
    return shutil.which("tesseract") is not None


def _extract_ocr_text(image) -> tuple[str, list[str], bool]:
    warnings: list[str] = []

    if not settings.IMAGE_OCR_ENABLED:
        warnings.append("IMAGE_OCR_ENABLED is false; OCR skipped")
        return "", warnings, False

    if not _tesseract_available():
        warnings.append("Tesseract OCR binary is not available on PATH")
        return "", warnings, False

    try:
        import pytesseract

        text = pytesseract.image_to_string(image)
        normalized = normalize_text(text)
        if normalized:
            return normalized, warnings, True
        warnings.append("OCR completed but no text was detected")
        return "", warnings, True
    except ImportError:
        pass
    except Exception as exc:
        warnings.append(f"pytesseract OCR failed: {exc}")

    with tempfile.NamedTemporaryFile(suffix=".png") as temp_file:
        image.save(temp_file.name, format=image.format or "PNG")
        command = [settings.TESSERACT_CMD or "tesseract", temp_file.name, "stdout"]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=settings.IMAGE_OCR_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            warnings.append("Tesseract OCR timed out")
            return "", warnings, False
        except OSError as exc:
            warnings.append(f"Tesseract OCR invocation failed: {exc}")
            return "", warnings, False

        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            warnings.append(f"Tesseract OCR failed: {stderr or completed.returncode}")
            return "", warnings, False

        normalized = normalize_text(completed.stdout)
        if normalized:
            return normalized, warnings, True
        warnings.append("OCR completed but no text was detected")
        return "", warnings, True


def parse_image(
    source: str | Path | BinaryIO,
    *,
    filename: str | None = None,
    chunk_size: int = 1800,
    chunk_overlap: int = 200,
) -> ParsedDocument:
    raw = read_bytes(source)
    source_name = source_name_for(source, filename, "uploaded.image")
    digest = source_hash(raw)
    metadata = {
        "parser": "image",
        "source": source_name,
        "source_hash": digest,
        "chunk_count": 0,
        "ocr_used": False,
    }
    warnings: list[str] = []
    chunks: list[ParsedChunk] = []

    try:
        from PIL import Image

        with Image.open(BytesIO(raw)) as image:
            metadata.update(
                {
                    "format": image.format,
                    "width": image.width,
                    "height": image.height,
                    "mode": image.mode,
                }
            )
            ocr_text, ocr_warnings, ocr_used = _extract_ocr_text(image)
            warnings.extend(ocr_warnings)
            metadata["ocr_used"] = ocr_used

            if ocr_text:
                for index, text in enumerate(
                    chunk_text(ocr_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap),
                    start=1,
                ):
                    chunks.append(
                        ParsedChunk(
                            source=source_name,
                            text=text,
                            metadata={
                                "parser": "image",
                                "source_hash": digest,
                                "ocr_used": True,
                                "chunk_index": index,
                                "chunk_size": len(text),
                                "format": image.format,
                                "width": image.width,
                                "height": image.height,
                            },
                        )
                    )
            elif not ocr_used:
                warnings.append(f"{source_name}: OCR is not configured; image metadata only")
    except ImportError:
        warnings.append("Pillow is not installed; image dimensions and OCR were skipped")
    except Exception as exc:
        warnings.append(f"{source_name}: image parsing failed: {exc}")

    metadata["chunk_count"] = len(chunks)
    return ParsedDocument(source=source_name, chunks=chunks, metadata=metadata, warnings=warnings)
