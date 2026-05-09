from pathlib import Path
from typing import BinaryIO

from ingestion.parsers.base import ParsedDocument, read_bytes, source_hash, source_name_for


def parse_image(
    source: str | Path | BinaryIO,
    *,
    filename: str | None = None,
) -> ParsedDocument:
    raw = read_bytes(source)
    source_name = source_name_for(source, filename, "uploaded.image")
    digest = source_hash(raw)
    metadata = {
        "parser": "image",
        "source": source_name,
        "source_hash": digest,
        "chunk_count": 0,
    }
    warnings = [f"{source_name}: OCR is not configured yet; image metadata only"]

    try:
        from PIL import Image

        from io import BytesIO

        with Image.open(BytesIO(raw)) as image:
            metadata.update(
                {
                    "format": image.format,
                    "width": image.width,
                    "height": image.height,
                    "mode": image.mode,
                }
            )
    except ImportError:
        warnings.append("Pillow is not installed; image dimensions and EXIF were skipped")
    except Exception as exc:
        warnings.append(f"{source_name}: image metadata extraction failed: {exc}")

    return ParsedDocument(source=source_name, chunks=[], metadata=metadata, warnings=warnings)
