"""OMPA (persistent memory) adapter.

Prefers the upstream ``ompa`` submodule when installed; otherwise uses the
production-shaped :class:`~app.storage.ompa_engine.OmpaEngine` fallback
which provides session tracking, structured classifications, tag filters,
and stats.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from app.core.config import get_settings
from app.storage.ompa_engine import OmpaEngine as LocalOmpaEngine

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency at scaffold stage
    from ompa import Ompa as _UpstreamOmpa  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    _UpstreamOmpa = None  # type: ignore[assignment]


def _select_engine_class() -> tuple[type[Any], str]:
    settings = get_settings()
    backend = settings.OMPA_BACKEND.lower()
    if backend == "submodule" and _UpstreamOmpa is not None:
        return _UpstreamOmpa, "submodule"
    if backend == "submodule":
        logger.warning(
            "OMPA_BACKEND=submodule but the ompa package is unavailable; "
            "falling back to the local journal engine"
        )
    return LocalOmpaEngine, "local"


class OmpaAdapter:
    def __init__(self, project_id: str):
        settings = get_settings()
        self.project_id = project_id
        self.vault_path = os.path.join(
            settings.OMPA_VAULT_ROOT, f"project_{project_id}"
        )
        os.makedirs(self.vault_path, exist_ok=True)

        engine_cls, backend = _select_engine_class()
        self.backend = backend
        self.ao: Any = engine_cls(vault_path=self.vault_path)

    async def record_decision(
        self,
        message: str,
        *,
        classification: str | None = None,
        tags: list[str] | None = None,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            return self.ao.classify(
                message,
                classification=classification,
                tags=tags,
                properties=properties,
            )
        except TypeError:
            return self.ao.classify(message)

    async def session_start(
        self, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        try:
            return self.ao.session_start(metadata)
        except TypeError:
            return self.ao.session_start()

    async def session_end(
        self, session_id: str | None = None
    ) -> dict[str, Any] | None:
        if hasattr(self.ao, "session_end"):
            try:
                return self.ao.session_end(session_id)
            except TypeError:
                return self.ao.session_end()
        return None

    async def entries(
        self,
        *,
        session_id: str | None = None,
        classification: str | None = None,
        tags: list[str] | None = None,
        limit: int | None = 100,
    ) -> list[dict[str, Any]]:
        if hasattr(self.ao, "entries"):
            try:
                return self.ao.entries(
                    session_id=session_id,
                    classification=classification,
                    tags=tags,
                    limit=limit,
                )
            except TypeError:
                return self.ao.entries()
        return []

    async def stats(self) -> dict[str, Any]:
        if hasattr(self.ao, "stats"):
            stats = self.ao.stats()
            if isinstance(stats, dict):
                stats.setdefault("backend", self.backend)
                stats.setdefault("project_id", self.project_id)
                return stats
        return {"backend": self.backend, "project_id": self.project_id}
