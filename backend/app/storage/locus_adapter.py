"""Locus (vectorless RAG) adapter.

Prefers the upstream ``locus`` submodule when installed; otherwise uses the
production-shaped :class:`~app.storage.locus_engine.LocusEngine` fallback
which now offers BM25 ranking, metadata filters, and persistent storage.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from app.core.config import get_settings
from app.storage.locus_engine import LocusEngine as LocalLocusEngine

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency at scaffold stage
    from locus import LocusEngine as _UpstreamLocusEngine  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    _UpstreamLocusEngine = None  # type: ignore[assignment]


def _select_engine_class() -> tuple[type[Any], str]:
    settings = get_settings()
    backend = settings.LOCUS_BACKEND.lower()
    if backend == "submodule" and _UpstreamLocusEngine is not None:
        return _UpstreamLocusEngine, "submodule"
    if backend == "submodule":
        logger.warning(
            "LOCUS_BACKEND=submodule but the locus package is unavailable; "
            "falling back to the local BM25 engine"
        )
    return LocalLocusEngine, "local"


class LocusAdapter:
    def __init__(self, project_id: str):
        settings = get_settings()
        self.project_id = project_id
        self.store_path = os.path.join(settings.LOCUS_ROOT, f"project_{project_id}")
        os.makedirs(self.store_path, exist_ok=True)

        engine_cls, backend = _select_engine_class()
        self.backend = backend
        self.engine: Any = engine_cls(store_path=self.store_path)

    async def index_files(self, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        result = self.engine.index(chunks)
        if isinstance(result, dict):
            return result
        return {"added": len(chunks)}

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        try:
            return self.engine.retrieve(query, limit=limit, filters=filters)
        except TypeError:
            # Upstream engine doesn't accept filters yet.
            return self.engine.retrieve(query, limit=limit)

    async def stats(self) -> dict[str, Any]:
        if hasattr(self.engine, "stats"):
            stats = self.engine.stats()
            if isinstance(stats, dict):
                stats.setdefault("backend", self.backend)
                stats.setdefault("project_id", self.project_id)
                return stats
        return {"backend": self.backend, "project_id": self.project_id}

    async def clear(self) -> None:
        if hasattr(self.engine, "clear"):
            self.engine.clear()
