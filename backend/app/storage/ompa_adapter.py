"""OMPA (persistent memory) adapter."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings

try:  # pragma: no cover - optional dependency at scaffold stage
    from ompa import Ompa  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    Ompa = None  # type: ignore[assignment]


@dataclass
class _InMemoryOmpa:
    vault_path: str
    entries: list[dict[str, Any]] = field(default_factory=list)
    session_id: str | None = None

    def classify(self, message: str) -> dict[str, Any]:
        entry = {
            "id": str(uuid.uuid4()),
            "session_id": self.session_id,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.entries.append(entry)
        os.makedirs(self.vault_path, exist_ok=True)
        with open(os.path.join(self.vault_path, "entries.json"), "w", encoding="utf-8") as fh:
            json.dump(self.entries, fh, indent=2)
        return entry

    def session_start(self) -> dict[str, Any]:
        self.session_id = str(uuid.uuid4())
        return {"session_id": self.session_id}


class OmpaAdapter:
    def __init__(self, project_id: str):
        settings = get_settings()
        self.project_id = project_id
        self.vault_path = os.path.join(settings.OMPA_VAULT_ROOT, f"project_{project_id}")
        os.makedirs(self.vault_path, exist_ok=True)

        if Ompa is not None:
            self.ao: Any = Ompa(vault_path=self.vault_path)
        else:
            self.ao = _InMemoryOmpa(vault_path=self.vault_path)

    async def record_decision(self, message: str) -> dict[str, Any]:
        return self.ao.classify(message)

    async def session_start(self) -> dict[str, Any]:
        return self.ao.session_start()
