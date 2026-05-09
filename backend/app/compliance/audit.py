import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.config import settings


class ComplianceAuditStore:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.COMPLIANCE_AUDIT_ROOT)

    def record(
        self,
        *,
        project_id: str,
        action: str,
        allowed: bool,
        profile: dict[str, Any],
        reason: str,
        redactions: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "id": f"audit_{uuid4().hex}",
            "project_id": project_id,
            "action": action,
            "allowed": allowed,
            "profile": profile,
            "reason": reason,
            "redactions": redactions or [],
            "metadata": metadata or {},
            "created_at": datetime.now(UTC).isoformat(),
        }
        project_dir = self.root / project_id
        os.makedirs(project_dir, exist_ok=True)
        with (project_dir / "events.jsonl").open("a") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
        return event

    def list_events(self, project_id: str, limit: int = 100) -> list[dict[str, Any]]:
        path = self.root / project_id / "events.jsonl"
        if not path.exists():
            return []
        events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        return events[-limit:]
