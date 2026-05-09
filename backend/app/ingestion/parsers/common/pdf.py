import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from pypdf import PdfReader


@dataclass(frozen=True)
class ParsedChunk:
    source: str
    text: str
    metadata: dict

    def as_dict(self) -> dict:
        return {
            "source": self.source,
            "text": self.text,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ParsedDocument:
    source: str
    chunks: list[ParsedChunk]
    metadata: dict
    warnings: list[str]


def parse_pdf(
    source: str | Path | BinaryIO,
    *,
    filename: str | None = None,
    chunk_size: int = 1800,
    chunk_overlap: int = 200,
) -> ParsedDocument:
    raw = _read_bytes(source)
    if filename:
        source_name = filename
    elif isinstance(source, (str, Path)):
        source_name = str(source)
    else:
        source_name = getattr(source, "name", None) or "uploaded.pdf"
    source_hash = hashlib.sha256(raw).hexdigest()
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

        normalized = _normalize_text(text)
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
                        "source_hash": source_hash,
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
        "source_hash": source_hash,
        "page_count": page_count,
        "chunk_count": len(chunks),
    }
    return ParsedDocument(
        source=source_name,
        chunks=chunks,
        metadata=document_metadata,
        warnings=warnings,
    )


def _read_bytes(source: str | Path | BinaryIO) -> bytes:
    if isinstance(source, (str, Path)):
        return Path(source).read_bytes()

    position = None
    if hasattr(source, "tell") and hasattr(source, "seek"):
        position = source.tell()
        source.seek(0)

    data = source.read()
    if isinstance(data, str):
        data = data.encode()

    if position is not None:
        source.seek(position)

    return data


def _as_binary_stream(raw: bytes):
    from io import BytesIO

    return BytesIO(raw)


def _normalize_text(text: str) -> str:
    lines = [line.strip() for line in text.replace("\x00", "").splitlines()]
    return "\n".join(line for line in lines if line)


def _chunk_text(text: str, *, chunk_size: int, chunk_overlap: int) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = end - chunk_overlap
    return chunks
