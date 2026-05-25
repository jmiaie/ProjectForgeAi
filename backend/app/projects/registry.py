import json
import os
import re
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from core.config import settings


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ProjectRecord(BaseModel):
    project_id: str
    name: str
    compliance: str = "standard"
    tier: str = "starter"
    status: ProjectStatus = ProjectStatus.ACTIVE
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ProjectRegistry:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.PROJECT_REGISTRY_ROOT)
        os.makedirs(self.root, exist_ok=True)

    def create(
        self,
        *,
        name: str,
        compliance: str = "standard",
        tier: str | None = None,
        project_id: str | None = None,
    ) -> ProjectRecord:
        record = ProjectRecord(
            project_id=project_id or _generate_project_id(name),
            name=name.strip() or "Untitled project",
            compliance=compliance.lower(),
            tier=(tier or settings.PROJECT_TIER).lower(),
        )
        self._write(record)
        self._refresh_index()
        return record

    def get(self, project_id: str) -> ProjectRecord | None:
        path = self.root / f"{project_id}.json"
        if not path.exists():
            return None
        return ProjectRecord.model_validate(json.loads(path.read_text()))

    def list_projects(self, *, include_archived: bool = False) -> list[ProjectRecord]:
        self._ensure_default_project()
        records: list[ProjectRecord] = []
        for path in sorted(self.root.glob("proj_*.json")):
            record = ProjectRecord.model_validate(json.loads(path.read_text()))
            if include_archived or record.status == ProjectStatus.ACTIVE:
                records.append(record)
        records.sort(key=lambda item: item.updated_at, reverse=True)
        return records

    def archive(self, project_id: str) -> ProjectRecord:
        record = self._require(project_id)
        updated = record.model_copy(
            update={
                "status": ProjectStatus.ARCHIVED,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
        self._write(updated)
        self._refresh_index()
        return updated

    def touch(self, project_id: str) -> ProjectRecord | None:
        record = self.get(project_id)
        if record is None:
            return None
        updated = record.model_copy(update={"updated_at": datetime.now(UTC).isoformat()})
        self._write(updated)
        self._refresh_index()
        return updated

    def _require(self, project_id: str) -> ProjectRecord:
        record = self.get(project_id)
        if record is None:
            raise ValueError(f"Unknown project: {project_id}")
        return record

    def _write(self, record: ProjectRecord) -> None:
        (self.root / f"{record.project_id}.json").write_text(
            json.dumps(record.as_dict(), indent=2, sort_keys=True)
        )

    def _refresh_index(self) -> None:
        index = [record.as_dict() for record in self.list_projects(include_archived=True)]
        (self.root / "index.json").write_text(json.dumps(index, indent=2, sort_keys=True))

    def _ensure_default_project(self) -> None:
        default_id = settings.DEFAULT_PROJECT_ID
        if self.get(default_id) is None:
            self.create(
                name="Starter Project",
                compliance=settings.DEFAULT_COMPLIANCE,
                tier=settings.PROJECT_TIER,
                project_id=default_id,
            )


def _generate_project_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:24]
    suffix = uuid4().hex[:8]
    return f"proj_{slug}-{suffix}" if slug else f"proj_{suffix}"
