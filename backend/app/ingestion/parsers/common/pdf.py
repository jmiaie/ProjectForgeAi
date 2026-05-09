from pathlib import Path
from typing import BinaryIO

from pypdf import PdfReader

from ingestion.parsers.base import (
    ParsedChunk,
    ParsedDocument,
    chunk_text,
    normalize_text,
    read_bytes,
    source_hash,
    source_name_for,
)


def parse_pdf(
    source: str | Path | BinaryIO,
    *,
    filename: str | None = None,
    chunk_size: int = 1800,
    chunk_overlap: int = 200,
) -> ParsedDocument:
    raw = read_bytes(source)
    source_name = source_name_for(source, filename, "uploaded.pdf")
    digest = source_hash(raw)
    warnings: list[str] = []
    chunks: list[ParsedChunk] = []

    reader = PdfReader(_as_binary_stream(raw))
    page_count = len(reader.pages)

    for page_index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:  # pypdf can raise on malformed page resources.
            text = ""
            warnings.append(f"Page {page_index}: text extraction failed: {exc}")

        normalized = normalize_text(text)
        if not normalized:
            warnings.append(f"Page {page_index}: no extractable text")
            continue

        for chunk_index, chunk_text in enumerate(
            _chunk_text(normalized, chunk_size=chunk_size, chunk_overlap=chunk_overlap),
            start=1,
        ):
            chunks.append(
                ParsedChunk(
                    source=source_name,
                    text=chunk_text,
                    metadata={
                        "parser": "pdf",
                        "source_hash": digest,
                        "page": page_index,
                        "page_count": page_count,
                        "chunk_index": chunk_index,
                        "chunk_size": len(chunk_text),
                    },
                )
            )

    document_metadata = {
        "parser": "pdf",
        "source": source_name,
        "source_hash": digest,
        "page_count": page_count,
        "chunk_count": len(chunks),
    }
    return ParsedDocument(
        source=source_name,
        chunks=chunks,
        metadata=document_metadata,
        warnings=warnings,
    )


def _as_binary_stream(raw: bytes):
    from io import BytesIO

    return BytesIO(raw)


def _chunk_text(text: str, *, chunk_size: int, chunk_overlap: int) -> list[str]:
    return chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
