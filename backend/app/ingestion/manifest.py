import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.config import settings
from ingestion.parsers.base import ParsedDocument


class IngestionManifestStore:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.INGESTION_MANIFEST_ROOT)

    def write(
        self,
        *,
        project_id: str,
        documents: list[ParsedDocument],
        storage: dict,
        session: Any,
    ) -> dict:
        timestamp = datetime.now(UTC).isoformat()
        manifest = {
            "project_id": project_id,
            "created_at": timestamp,
            "files_processed": len(documents),
            "chunks_indexed": sum(len(document.chunks) for document in documents),
            "warnings": [warning for document in documents for warning in document.warnings],
            "documents": [
                {
                    "source": document.source,
                    "metadata": document.metadata,
                    "warnings": document.warnings,
                    "chunks": [chunk.metadata for chunk in document.chunks],
                }
                for document in documents
            ],
            "storage": storage,
            "session": session,
        }

        project_dir = self.root / project_id
        os.makedirs(project_dir, exist_ok=True)
        manifest_path = project_dir / "latest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
        manifest["path"] = str(manifest_path)
        return manifest

    def read_latest(self, project_id: str) -> dict | None:
        manifest_path = self.root / project_id / "latest.json"
        if not manifest_path.exists():
            return None
        manifest = json.loads(manifest_path.read_text())
        manifest["path"] = str(manifest_path)
        return manifest
