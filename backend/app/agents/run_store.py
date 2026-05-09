import json
import os
from pathlib import Path

from agents.state import OrchestratorRun
from core.config import settings


class OrchestratorRunStore:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.ORCHESTRATION_RUN_ROOT)

    def write(self, run: OrchestratorRun) -> dict:
        project_dir = self.root / run.project_id
        os.makedirs(project_dir, exist_ok=True)
        run_path = project_dir / f"{run.run_id}.json"
        payload = run.model_dump(mode="json")
        payload["path"] = str(run_path)
        run_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

        latest_path = project_dir / "latest.json"
        latest_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
        return payload

    def read(self, project_id: str, run_id: str | None = None) -> dict | None:
        project_dir = self.root / project_id
        path = project_dir / f"{run_id}.json" if run_id else project_dir / "latest.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text())
        payload["path"] = str(path)
        return payload
