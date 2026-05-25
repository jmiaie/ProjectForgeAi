import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from cryptography.fernet import Fernet

from core.config import settings
from integrations.connection_store import _fernet_key


class LLMKeyStore:
    def __init__(self, root: str | None = None, encryption_key: str | None = None):
        self.root = Path(root or settings.LLM_KEY_ROOT)
        self.fernet = Fernet(_fernet_key(encryption_key or settings.ENCRYPTION_KEY))

    def upsert(self, *, project_id: str, provider: str, api_key: str) -> dict[str, Any]:
        record = {
            "project_id": project_id,
            "provider": provider.lower(),
            "key_id": f"key_{uuid4().hex[:12]}",
            "updated_at": datetime.now(UTC).isoformat(),
            "encrypted_api_key": self.fernet.encrypt(api_key.encode()).decode(),
        }
        project_dir = self.root / project_id
        os.makedirs(project_dir, exist_ok=True)
        (project_dir / f"{provider.lower()}.json").write_text(
            json.dumps(record, indent=2, sort_keys=True)
        )
        return self._public(record)

    def get_secret(self, project_id: str, provider: str) -> str | None:
        path = self.root / project_id / f"{provider.lower()}.json"
        if not path.exists():
            return None
        record = json.loads(path.read_text())
        return self.fernet.decrypt(record["encrypted_api_key"].encode()).decode()

    def list_keys(self, project_id: str) -> list[dict[str, Any]]:
        project_dir = self.root / project_id
        if not project_dir.exists():
            return []
        return [
            self._public(json.loads(path.read_text()))
            for path in sorted(project_dir.glob("*.json"))
        ]

    def delete(self, project_id: str, provider: str) -> bool:
        path = self.root / project_id / f"{provider.lower()}.json"
        if not path.exists():
            return False
        path.unlink()
        return True

    def resolve_api_key(self, project_id: str, model: str) -> str | None:
        provider = model.split("/", 1)[0] if "/" in model else model
        return self.get_secret(project_id, provider)

    @staticmethod
    def _public(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "project_id": record["project_id"],
            "provider": record["provider"],
            "key_id": record["key_id"],
            "updated_at": record["updated_at"],
            "configured": True,
        }
