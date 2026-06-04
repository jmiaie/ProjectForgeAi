"""Context optimization for orchestrator retrieval.

Trims Locus chunks to a configurable character / count budget before they
are passed to specialist agents. When the ``rtk`` CLI is available on PATH,
metadata records that RTK compression is enabled (future hook for delegating
to the upstream tool).
"""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.storage.rtk_adapter import RTKAdapter


def optimize_context_chunks(
    chunks: list[dict[str, Any]],
    *,
    max_chunks: int | None = None,
    max_chars: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return trimmed chunks plus optimization metadata."""

    settings = get_settings()
    limit_chunks = max_chunks if max_chunks is not None else settings.RTK_MAX_CONTEXT_CHUNKS
    limit_chars = max_chars if max_chars is not None else settings.RTK_MAX_CONTEXT_CHARS

    rtk = RTKAdapter(enabled=settings.RTK_ENABLED)
    original_count = len(chunks)
    original_chars = sum(len(str(c.get("text", ""))) for c in chunks)

    trimmed: list[dict[str, Any]] = []
    used_chars = 0
    for chunk in chunks[:limit_chunks]:
        text = str(chunk.get("text", ""))
        if not text:
            continue
        remaining = limit_chars - used_chars
        if remaining <= 0:
            break
        if len(text) > remaining:
            piece = dict(chunk)
            piece["text"] = text[:remaining]
            piece["metadata"] = {
                **(chunk.get("metadata") or {}),
                "rtk_truncated": True,
            }
            trimmed.append(piece)
            used_chars += remaining
            break
        trimmed.append(chunk)
        used_chars += len(text)

    meta = {
        "rtk_enabled": settings.RTK_ENABLED,
        "rtk_cli_available": rtk.enabled,
        "original_chunks": original_count,
        "original_chars": original_chars,
        "optimized_chunks": len(trimmed),
        "optimized_chars": used_chars,
    }
    return trimmed, meta
