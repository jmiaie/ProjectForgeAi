import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


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


def read_bytes(source: str | Path | BinaryIO) -> bytes:
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


def source_name_for(source: str | Path | BinaryIO, filename: str | None, fallback: str) -> str:
    if filename:
        return filename
    if isinstance(source, (str, Path)):
        return str(source)
    return getattr(source, "name", None) or fallback


def source_hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def normalize_text(text: str) -> str:
    lines = [line.strip() for line in text.replace("\x00", "").splitlines()]
    return "\n".join(line for line in lines if line)


def chunk_text(text: str, *, chunk_size: int, chunk_overlap: int) -> list[str]:
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
