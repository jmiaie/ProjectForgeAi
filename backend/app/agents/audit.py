import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.config import settings


class OrchestratorAuditStore:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.ORCHESTRATION_RUN_ROOT) / "_audit"

    def record(
        self,
        *,
        project_id: str,
        run_id: str,
        event_type: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "id": f"orch_audit_{uuid4().hex}",
            "project_id": project_id,
            "run_id": run_id,
            "event_type": event_type,
            "message": message,
            "metadata": metadata or {},
            "created_at": datetime.now(UTC).isoformat(),
        }
        project_dir = self.root / project_id
        os.makedirs(project_dir, exist_ok=True)
        with (project_dir / "events.jsonl").open("a") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
        return event

    def list_events(
        self,
        project_id: str,
        run_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        path = self.root / project_id / "events.jsonl"
        if not path.exists():
            return []
        events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        if run_id:
            events = [event for event in events if event.get("run_id") == run_id]
        return events[-limit:]
