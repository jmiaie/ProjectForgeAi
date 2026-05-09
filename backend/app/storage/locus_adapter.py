"""Locus (vectorless RAG) storage adapter.

The adapter falls back to a pure in-process store when the ``locus`` package
is not installed, so the rest of the pipeline can operate end-to-end during
the scaffold phase.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from app.core.config import get_settings

try:  # pragma: no cover - optional dependency at scaffold stage
    from locus import LocusEngine  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    LocusEngine = None  # type: ignore[assignment]


@dataclass
class _InMemoryLocus:
    """Tiny stand-in used when the real Locus engine is unavailable."""

    store_path: str
    chunks: list[dict[str, Any]] = field(default_factory=list)

    def index(self, chunks: list[dict[str, Any]]) -> None:
        self.chunks.extend(chunks)
        os.makedirs(self.store_path, exist_ok=True)
        with open(os.path.join(self.store_path, "chunks.json"), "w", encoding="utf-8") as fh:
            json.dump(self.chunks, fh, indent=2)

    def retrieve(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        q = query.lower()
        scored = [
            (chunk, sum(token in chunk.get("text", "").lower() for token in q.split()))
            for chunk in self.chunks
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        return [chunk for chunk, score in scored[:limit] if score > 0]


class LocusAdapter:
    def __init__(self, project_id: str):
        settings = get_settings()
        self.project_id = project_id
        self.store_path = os.path.join(settings.LOCUS_ROOT, f"project_{project_id}")
        os.makedirs(self.store_path, exist_ok=True)

        if LocusEngine is not None:
            self.engine: Any = LocusEngine(store_path=self.store_path)
        else:
            self.engine = _InMemoryLocus(store_path=self.store_path)

    async def index_files(self, chunks: list[dict[str, Any]]) -> None:
        self.engine.index(chunks)

    async def retrieve(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        return self.engine.retrieve(query, limit=limit)
