import json
import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from compliance.audit import ComplianceAuditStore
from compliance.redaction import RedactionResult, redact_text
from core.config import settings


class ComplianceCategory(StrEnum):
    STANDARD = "standard"
    HIPAA = "hipaa"
    LEGAL = "legal"
    SOC2 = "soc2"
    GDPR = "gdpr"


@dataclass(frozen=True)
class ComplianceProfile:
    project_id: str
    category: str
    allow_self_learning: bool = True
    allow_memory_writes: bool = True
    require_human_approval_for_external_writes: bool = False
    redact_before_llm: bool = False
    required_model: str | None = None
    audit_required: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "category": self.category,
            "allow_self_learning": self.allow_self_learning,
            "allow_memory_writes": self.allow_memory_writes,
            "require_human_approval_for_external_writes": self.require_human_approval_for_external_writes,
            "redact_before_llm": self.redact_before_llm,
            "required_model": self.required_model,
            "audit_required": self.audit_required,
        }


@dataclass(frozen=True)
class ComplianceDecision:
    allowed: bool
    action: str
    reason: str
    profile: ComplianceProfile
    redactions: list[dict[str, Any]]
    payload: Any = None


POLICIES: dict[str, dict[str, Any]] = {
    ComplianceCategory.STANDARD.value: {
        "allow_self_learning": True,
        "allow_memory_writes": True,
        "require_human_approval_for_external_writes": False,
        "redact_before_llm": False,
        "required_model": None,
    },
    ComplianceCategory.HIPAA.value: {
        "allow_self_learning": False,
        "allow_memory_writes": False,
        "require_human_approval_for_external_writes": True,
        "redact_before_llm": True,
        "required_model": "anthropic/claude-3-5-sonnet-20241022",
    },
    ComplianceCategory.LEGAL.value: {
        "allow_self_learning": False,
        "allow_memory_writes": False,
        "require_human_approval_for_external_writes": True,
        "redact_before_llm": True,
        "required_model": "anthropic/claude-3-5-sonnet-20241022",
    },
    ComplianceCategory.SOC2.value: {
        "allow_self_learning": True,
        "allow_memory_writes": True,
        "require_human_approval_for_external_writes": True,
        "redact_before_llm": False,
        "required_model": None,
    },
    ComplianceCategory.GDPR.value: {
        "allow_self_learning": False,
        "allow_memory_writes": False,
        "require_human_approval_for_external_writes": True,
        "redact_before_llm": True,
        "required_model": None,
    },
}


class ComplianceProfileStore:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.COMPLIANCE_PROFILE_ROOT)

    def set(self, project_id: str, category: str) -> ComplianceProfile:
        profile = build_profile(project_id, category)
        project_dir = self.root / project_id
        os.makedirs(project_dir, exist_ok=True)
        (project_dir / "profile.json").write_text(json.dumps(profile.as_dict(), indent=2, sort_keys=True))
        return profile

    def get(self, project_id: str) -> ComplianceProfile | None:
        path = self.root / project_id / "profile.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return ComplianceProfile(**data)


class ComplianceEnforcer:
    def __init__(
        self,
        profile_store: ComplianceProfileStore | None = None,
        audit_store: ComplianceAuditStore | None = None,
    ):
        self.profile_store = profile_store or ComplianceProfileStore()
        self.audit_store = audit_store or ComplianceAuditStore()

    def get_profile(self, project_id: str) -> ComplianceProfile:
        return self.profile_store.get(project_id) or build_profile(project_id, settings.DEFAULT_COMPLIANCE)

    def set_profile(self, project_id: str, category: str) -> ComplianceProfile:
        profile = self.profile_store.set(project_id, category)
        self.audit_store.record(
            project_id=project_id,
            action="profile_set",
            allowed=True,
            profile=profile.as_dict(),
            reason=f"Profile set to {profile.category}",
        )
        return profile

    def check_action(self, project_id: str, action: str, payload: Any = None) -> ComplianceDecision:
        profile = self.get_profile(project_id)
        allowed = True
        reason = "Allowed by compliance profile"
        sanitized_payload = payload
        redactions: list[dict[str, Any]] = []

        if action == "memory_write" and not profile.allow_memory_writes:
            allowed = False
            reason = f"{profile.category} profile blocks ungated memory writes"
        elif action == "self_learning" and not profile.allow_self_learning:
            allowed = False
            reason = f"{profile.category} profile blocks self-learning and adaptive improvements"
        elif action == "external_write" and profile.require_human_approval_for_external_writes:
            allowed = False
            reason = f"{profile.category} profile requires human approval for external writes"
        elif action == "llm_call" and profile.redact_before_llm:
            sanitized_payload, redactions = self._redact_payload(payload)
            reason = "Allowed after pre-LLM redaction"

        self.audit_store.record(
            project_id=project_id,
            action=action,
            allowed=allowed,
            profile=profile.as_dict(),
            reason=reason,
            redactions=redactions,
            metadata={"payload_type": type(payload).__name__},
        )
        return ComplianceDecision(
            allowed=allowed,
            action=action,
            reason=reason,
            profile=profile,
            redactions=redactions,
            payload=sanitized_payload,
        )

    def audit_events(self, project_id: str, limit: int = 100) -> list[dict[str, Any]]:
        return self.audit_store.list_events(project_id, limit)

    def _redact_payload(self, payload: Any) -> tuple[Any, list[dict[str, Any]]]:
        if isinstance(payload, str):
            result = redact_text(payload)
            return result.text, result.as_dicts()
        if isinstance(payload, list):
            redactions: list[dict[str, Any]] = []
            sanitized = []
            for item in payload:
                sanitized_item, item_redactions = self._redact_payload(item)
                sanitized.append(sanitized_item)
                redactions.extend(item_redactions)
            return sanitized, redactions
        if isinstance(payload, dict):
            redactions = []
            sanitized = {}
            for key, value in payload.items():
                if key == "content" and isinstance(value, str):
                    result: RedactionResult = redact_text(value)
                    sanitized[key] = result.text
                    redactions.extend(result.as_dicts())
                else:
                    sanitized_value, value_redactions = self._redact_payload(value)
                    sanitized[key] = sanitized_value
                    redactions.extend(value_redactions)
            return sanitized, redactions
        return payload, []


def get_compliance_profile(project_id: str) -> ComplianceProfile:
    return ComplianceEnforcer().get_profile(project_id)


def build_profile(project_id: str, category: str) -> ComplianceProfile:
    normalized = category.lower()
    if normalized not in POLICIES:
        normalized = ComplianceCategory.STANDARD.value
    policy = POLICIES[normalized]
    return ComplianceProfile(project_id=project_id, category=normalized, **policy)
