from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from automations.models import AutomationDefinition, AutomationRunResult, AutomationStatus
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

    def append_dead_letter(self, result: AutomationRunResult) -> dict:
        project_dir = self.root / result.project_id
        os.makedirs(project_dir, exist_ok=True)
        path = project_dir / "dead_letters.jsonl"
        payload = result.model_dump(mode="json")
        with path.open("a") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
        return payload

    def list_dead_letters(self, project_id: str, limit: int = 100) -> list[dict]:
        path = self.root / project_id / "dead_letters.jsonl"
        if not path.exists():
            return []
        records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        return records[-limit:]

    def list_projects(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted(path.name for path in self.root.iterdir() if path.is_dir())

    def list_due(self) -> list[AutomationDefinition]:
        due: list[AutomationDefinition] = []
        now = datetime.now(UTC)
        for project_id in self.list_projects():
            for record in self.list(project_id):
                automation = AutomationDefinition(**{key: value for key, value in record.items() if key != "path"})
                if automation.status not in {AutomationStatus.SCHEDULED, AutomationStatus.FAILED}:
                    continue
                if automation.next_retry_at is None:
                    continue
                retry_at = datetime.fromisoformat(automation.next_retry_at)
                if retry_at <= now:
                    due.append(automation)
        return due
