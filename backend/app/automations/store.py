from __future__ import annotations

import json
import os
from pathlib import Path

from automations.models import AutomationDefinition, AutomationRunResult
from core.config import settings


class AutomationStore:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.AUTOMATION_WORKFLOW_ROOT)

    def upsert(self, automation: AutomationDefinition) -> dict:
        project_dir = self.root / automation.project_id
        os.makedirs(project_dir, exist_ok=True)
        path = project_dir / f"{automation.id}.json"
        payload = automation.model_dump(mode="json")
        payload["path"] = str(path)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))
        return payload

    def get(self, project_id: str, automation_id: str) -> AutomationDefinition | None:
        path = self.root / project_id / f"{automation_id}.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text())
        payload.pop("path", None)
        return AutomationDefinition(**payload)

    def list(self, project_id: str) -> list[dict]:
        project_dir = self.root / project_id
        if not project_dir.exists():
            return []
        records = []
        for path in sorted(project_dir.glob("auto_*.json")):
            payload = json.loads(path.read_text())
            payload["path"] = str(path)
            records.append(payload)
        return records

    def append_run(self, result: AutomationRunResult) -> dict:
        project_dir = self.root / result.project_id
        os.makedirs(project_dir, exist_ok=True)
        path = project_dir / "runs.jsonl"
        payload = result.model_dump(mode="json")
        with path.open("a") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
        return payload

    def list_runs(self, project_id: str, limit: int = 100) -> list[dict]:
        path = self.root / project_id / "runs.jsonl"
        if not path.exists():
            return []
        records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        return records[-limit:]
