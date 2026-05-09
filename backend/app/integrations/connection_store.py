import base64
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

from core.config import settings


class ConnectionStore:
    def __init__(self, root: str | None = None, encryption_key: str | None = None):
        self.root = Path(root or settings.INTEGRATIONS_CONNECTION_ROOT)
        self.fernet = Fernet(_fernet_key(encryption_key or settings.ENCRYPTION_KEY))

    def upsert(
        self,
        *,
        project_id: str,
        connector_type: str,
        connection: dict[str, Any],
    ) -> dict[str, Any]:
        record = {
            "project_id": project_id,
            "connector_type": connector_type,
            "connection_id": connection.get("id") or f"{connector_type}_{project_id}",
            "status": "connected",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "summary": _safe_summary(connection),
            "encrypted_connection": self.fernet.encrypt(
                json.dumps(connection, default=str, sort_keys=True).encode()
            ).decode(),
        }
        project_dir = self.root / project_id
        os.makedirs(project_dir, exist_ok=True)
        (project_dir / f"{connector_type}.json").write_text(json.dumps(record, indent=2, sort_keys=True))
        return _public_record(record)

    def get(self, project_id: str, connector_type: str) -> dict[str, Any] | None:
        path = self.root / project_id / f"{connector_type}.json"
        if not path.exists():
            return None
        return _public_record(json.loads(path.read_text()))

    def list(self, project_id: str) -> list[dict[str, Any]]:
        project_dir = self.root / project_id
        if not project_dir.exists():
            return []
        return [_public_record(json.loads(path.read_text())) for path in sorted(project_dir.glob("*.json"))]

    def load_secret(self, project_id: str, connector_type: str) -> dict[str, Any] | None:
        path = self.root / project_id / f"{connector_type}.json"
        if not path.exists():
            return None
        record = json.loads(path.read_text())
        return json.loads(self.fernet.decrypt(record["encrypted_connection"].encode()).decode())


def _fernet_key(raw_key: str) -> bytes:
    digest = hashlib.sha256(raw_key.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _safe_summary(connection: dict[str, Any]) -> dict[str, Any]:
    safe = {}
    for key, value in connection.items():
        if key.lower() in {"token", "access_token", "refresh_token", "api_key", "client_secret", "client"}:
            continue
        safe[key] = value
    return safe


def _public_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": record["project_id"],
        "connector_type": record["connector_type"],
        "connection_id": record["connection_id"],
        "status": record["status"],
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
        "summary": record.get("summary", {}),
    }
