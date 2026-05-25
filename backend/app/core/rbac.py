import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from core.config import settings


class ProjectRole(StrEnum):
    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"
    OWNER = "owner"


ROLE_PERMISSIONS: dict[str, set[str]] = {
    ProjectRole.VIEWER.value: {
        "project.read",
        "graph.read",
        "orchestrator.read",
        "compliance.read",
        "integrations.read",
        "automations.read",
    },
    ProjectRole.EDITOR.value: {
        "project.read",
        "graph.read",
        "graph.write",
        "orchestrator.read",
        "orchestrator.run",
        "compliance.read",
        "integrations.read",
        "integrations.connect",
        "automations.read",
        "automations.run",
        "workbench.query",
    },
    ProjectRole.ADMIN.value: {
        "project.read",
        "graph.read",
        "graph.write",
        "orchestrator.read",
        "orchestrator.run",
        "compliance.read",
        "compliance.set",
        "compliance.export",
        "integrations.read",
        "integrations.connect",
        "automations.read",
        "automations.run",
        "automations.approve",
        "workbench.query",
        "access.manage",
    },
    ProjectRole.OWNER.value: {
        "project.read",
        "graph.read",
        "graph.write",
        "orchestrator.read",
        "orchestrator.run",
        "compliance.read",
        "compliance.set",
        "compliance.export",
        "integrations.read",
        "integrations.connect",
        "automations.read",
        "automations.run",
        "automations.approve",
        "workbench.query",
        "access.manage",
        "upgrade.manage",
        "self_learning.run",
    },
}


@dataclass(frozen=True)
class ActorContext:
    actor_id: str
    role: str

    def as_dict(self) -> dict[str, str]:
        return {"actor_id": self.actor_id, "role": self.role}


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    action: str
    reason: str
    actor: ActorContext
    role: str


class RBACStore:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.RBAC_MEMBERSHIP_ROOT)

    def assign(self, project_id: str, actor_id: str, role: str) -> dict[str, Any]:
        normalized_role = role.lower()
        if normalized_role not in ROLE_PERMISSIONS:
            raise ValueError(f"Unknown role: {role}")

        project_dir = self.root / project_id
        os.makedirs(project_dir, exist_ok=True)
        record = {
            "actor_id": actor_id,
            "role": normalized_role,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        (project_dir / f"{actor_id}.json").write_text(json.dumps(record, indent=2, sort_keys=True))
        return record

    def get_role(self, project_id: str, actor_id: str) -> str | None:
        path = self.root / project_id / f"{actor_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text()).get("role")

    def list_members(self, project_id: str) -> list[dict[str, Any]]:
        project_dir = self.root / project_id
        if not project_dir.exists():
            return []
        members = []
        for path in sorted(project_dir.glob("*.json")):
            members.append(json.loads(path.read_text()))
        return members


class RBACService:
    def __init__(self, store: RBACStore | None = None):
        self.store = store or RBACStore()

    def resolve_actor(self, actor_id: str | None, role: str | None) -> ActorContext:
        return ActorContext(
            actor_id=actor_id or settings.RBAC_DEFAULT_ACTOR,
            role=(role or settings.RBAC_DEFAULT_ROLE).lower(),
        )

    def effective_role(self, project_id: str, actor: ActorContext) -> str:
        stored = self.store.get_role(project_id, actor.actor_id)
        if stored:
            return stored
        return actor.role

    def check(self, project_id: str, actor: ActorContext, action: str) -> AccessDecision:
        if not settings.RBAC_ENFORCE:
            return AccessDecision(
                allowed=True,
                action=action,
                reason="RBAC enforcement disabled",
                actor=actor,
                role=self.effective_role(project_id, actor),
            )

        role = self.effective_role(project_id, actor)
        permissions = ROLE_PERMISSIONS.get(role, set())
        allowed = action in permissions
        reason = "Allowed by project role" if allowed else f"Role '{role}' lacks permission '{action}'"
        return AccessDecision(
            allowed=allowed,
            action=action,
            reason=reason,
            actor=actor,
            role=role,
        )

    def require(self, project_id: str, actor: ActorContext, action: str) -> AccessDecision:
        decision = self.check(project_id, actor, action)
        if not decision.allowed:
            raise PermissionError(decision.reason)
        return decision

    def assign_member(self, project_id: str, actor_id: str, role: str) -> dict[str, Any]:
        return self.store.assign(project_id, actor_id, role)

    def list_members(self, project_id: str) -> list[dict[str, Any]]:
        return self.store.list_members(project_id)
