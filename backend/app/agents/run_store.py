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

    def write_checkpoint(self, run: OrchestratorRun) -> dict:
        project_dir = self.root / run.project_id
        checkpoint_dir = project_dir / "checkpoints" / run.run_id
        os.makedirs(checkpoint_dir, exist_ok=True)
        payload = run.model_dump(mode="json")
        step_index = len(run.steps)
        checkpoint_path = checkpoint_dir / f"step_{step_index:02d}.json"
        checkpoint_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
        return self.write(run)

    def read(self, project_id: str, run_id: str | None = None) -> dict | None:
        project_dir = self.root / project_id
        path = project_dir / f"{run_id}.json" if run_id else project_dir / "latest.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text())
        payload["path"] = str(path)
        return payload

    def list_runs(self, project_id: str, limit: int = 20) -> list[dict]:
        project_dir = self.root / project_id
        if not project_dir.exists():
            return []
        runs = []
        for path in sorted(project_dir.glob("run_*.json"), reverse=True):
            payload = json.loads(path.read_text())
            runs.append(
                {
                    "run_id": payload.get("run_id"),
                    "status": payload.get("status"),
                    "goal": payload.get("goal"),
                    "created_at": payload.get("created_at"),
                    "completed_at": payload.get("completed_at"),
                    "step_count": len(payload.get("steps", [])),
                }
            )
            if len(runs) >= limit:
                break
        return runs
