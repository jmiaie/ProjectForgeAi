import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from core.config import settings


class OAuthStateStore:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.INTEGRATIONS_CONNECTION_ROOT) / "oauth_states"
        self.root.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        *,
        state: str,
        connector_type: str,
        code_verifier: str,
        project_id: str | None,
        redirect_uri: str,
    ) -> dict:
        payload = {
            "state": state,
            "connector_type": connector_type,
            "code_verifier": code_verifier,
            "project_id": project_id,
            "redirect_uri": redirect_uri,
            "created_at": datetime.now(UTC).isoformat(),
        }
        path = self.root / f"{state}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))
        return payload

    def consume(self, state: str | None) -> dict | None:
        if not state:
            return None
        path = self.root / f"{state}.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text())
        path.unlink(missing_ok=True)
        created_at = datetime.fromisoformat(payload["created_at"])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if created_at + timedelta(minutes=15) < datetime.now(UTC):
            return None
        return payload
