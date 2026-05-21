"""Text chunking helpers used by parsers.

Sliding-window split with overlap, paragraph-aware so we don't slice mid
sentence when avoidable. Used by the hardened PDF parser to break long
pages into LLM-friendly chunks before indexing.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkingOptions:
    chunk_size: int = 1500
    overlap: int = 150
    min_chunk_size: int = 200

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if self.overlap < 0 or self.overlap >= self.chunk_size:
            raise ValueError("overlap must be in [0, chunk_size)")
        if self.min_chunk_size < 0:
            raise ValueError("min_chunk_size must be >= 0")


_DEFAULT_OPTIONS = ChunkingOptions()


def chunk_text(text: str, options: ChunkingOptions | None = None) -> list[str]:
    """Split ``text`` into overlapping chunks.

    The splitter prefers to break on paragraph boundaries (``\\n\\n``) and
    sentence boundaries (``. ``, ``! ``, ``? ``) within the configured
    window. Trailing fragments smaller than ``min_chunk_size`` are merged
    into the previous chunk so we don't emit a tiny tail.
    """

    opts = options or _DEFAULT_OPTIONS
    cleaned = text.strip()
    if not cleaned:
        return []
    if len(cleaned) <= opts.chunk_size:
        return [cleaned]

    chunks: list[str] = []
    cursor = 0
    length = len(cleaned)
    while cursor < length:
        end = min(cursor + opts.chunk_size, length)
        if end < length:
            split_at = _find_break(cleaned, cursor, end)
            if split_at > cursor:
                end = split_at
        chunk = cleaned[cursor:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        cursor = max(end - opts.overlap, cursor + 1)

    if (
        len(chunks) >= 2
        and len(chunks[-1]) < opts.min_chunk_size
    ):
        tail = chunks.pop()
        chunks[-1] = (chunks[-1] + " " + tail).strip()

    return chunks


def _find_break(text: str, start: int, end: int) -> int:
    """Return the latest sensible break index in ``text[start:end]``."""

    window = text[start:end]
    for delimiter in ("\n\n", ". ", "! ", "? ", "\n"):
        idx = window.rfind(delimiter)
        if idx > 0:
            return start + idx + len(delimiter)
    return end
