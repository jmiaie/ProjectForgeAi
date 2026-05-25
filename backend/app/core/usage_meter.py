import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.config import settings


class LLMUsageMeter:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.LLM_USAGE_ROOT)

    def record(
        self,
        *,
        project_id: str,
        model: str,
        task_type: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        routing_tier: str = "economy",
        used_byo_key: bool = False,
    ) -> dict[str, Any]:
        event = {
            "id": f"usage_{uuid4().hex}",
            "project_id": project_id,
            "model": model,
            "task_type": task_type,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "routing_tier": routing_tier,
            "used_byo_key": used_byo_key,
            "created_at": datetime.now(UTC).isoformat(),
        }
        project_dir = self.root / project_id
        os.makedirs(project_dir, exist_ok=True)
        with (project_dir / "events.jsonl").open("a") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
        return event

    def summary(self, project_id: str, limit: int = 100) -> dict[str, Any]:
        path = self.root / project_id / "events.jsonl"
        if not path.exists():
            return {
                "project_id": project_id,
                "call_count": 0,
                "total_tokens": 0,
                "flagship_calls": 0,
                "by_model": {},
                "recent": [],
            }

        events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        recent = events[-limit:]
        by_model: dict[str, int] = {}
        total_tokens = 0
        flagship_calls = 0
        for event in events:
            total_tokens += int(event.get("total_tokens", 0))
            model = event.get("model", "unknown")
            by_model[model] = by_model.get(model, 0) + 1
            if event.get("routing_tier") == "flagship":
                flagship_calls += 1

        return {
            "project_id": project_id,
            "call_count": len(events),
            "total_tokens": total_tokens,
            "flagship_calls": flagship_calls,
            "by_model": by_model,
            "recent": recent[-20:],
        }
