from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


POLICY_MODELS = {
    "standard": {
        "default_model": "groq/llama-3.1-70b-versatile",
        "allowed_models": {
            "groq/llama-3.1-70b-versatile",
            "openai/gpt-4o-mini",
            "anthropic/claude-3-5-haiku-20241022",
        },
    },
    "hipaa": {
        "default_model": "anthropic/claude-3-5-sonnet-20241022",
        "allowed_models": {
            "anthropic/claude-3-5-sonnet-20241022",
            "openai/gpt-4o-mini",
        },
    },
    "legal": {
        "default_model": "anthropic/claude-3-5-sonnet-20241022",
        "allowed_models": {
            "anthropic/claude-3-5-sonnet-20241022",
            "openai/gpt-4o-mini",
        },
    },
    "soc2": {
        "default_model": "groq/llama-3.1-70b-versatile",
        "allowed_models": {
            "groq/llama-3.1-70b-versatile",
            "openai/gpt-4o-mini",
            "anthropic/claude-3-5-haiku-20241022",
        },
    },
}


@dataclass
class ComplianceProfile:
    project_id: str
    category: str = "standard"
    last_updated: str | None = None


class InMemoryComplianceStateBackend:
    def __init__(self) -> None:
        self._profiles: dict[str, dict[str, Any]] = {}
        self._events: list[dict[str, Any]] = []

    def upsert_compliance_profile(self, project_id: str, category: str, last_updated: str) -> dict[str, Any]:
        profile = {"project_id": project_id, "category": category, "last_updated": last_updated}
        self._profiles[project_id] = profile
        return profile

    def get_compliance_profile(self, project_id: str) -> dict[str, Any] | None:
        return self._profiles.get(project_id)

    def add_audit_event(self, event: dict[str, Any]) -> dict[str, Any]:
        self._events.append(event)
        return event

    def list_audit_events(self, project_id: str, limit: int = 100) -> list[dict[str, Any]]:
        events = [event for event in self._events if event["project_id"] == project_id]
        return events[-limit:]


_STATE_BACKEND: Any = InMemoryComplianceStateBackend()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def configure_state_backend(state_backend: Any) -> None:
    global _STATE_BACKEND
    _STATE_BACKEND = state_backend


def set_compliance_profile(project_id: str, category: str) -> ComplianceProfile:
    normalized = category.lower()
    if normalized not in POLICY_MODELS:
        raise ValueError(f"Unsupported compliance category: {category}")
    persisted = _STATE_BACKEND.upsert_compliance_profile(
        project_id=project_id, category=normalized, last_updated=_now_iso()
    )
    profile = ComplianceProfile(
        project_id=persisted["project_id"],
        category=persisted["category"],
        last_updated=persisted["last_updated"],
    )
    record_audit_event(
        project_id=project_id,
        event_type="compliance_profile_updated",
        payload={"category": normalized},
    )
    return profile


def get_compliance_profile(project_id: str) -> ComplianceProfile:
    persisted = _STATE_BACKEND.get_compliance_profile(project_id)
    if persisted:
        return ComplianceProfile(
            project_id=persisted["project_id"],
            category=persisted["category"],
            last_updated=persisted["last_updated"],
        )
    default = _STATE_BACKEND.upsert_compliance_profile(
        project_id=project_id, category="standard", last_updated=_now_iso()
    )
    return ComplianceProfile(
        project_id=default["project_id"],
        category=default["category"],
        last_updated=default["last_updated"],
    )


def resolve_model_for_profile(
    project_id: str, requested_model: str | None, fallback_default_model: str
) -> tuple[ComplianceProfile, str]:
    profile = get_compliance_profile(project_id)
    policy = POLICY_MODELS.get(profile.category, POLICY_MODELS["standard"])
    default_model = policy["default_model"] or fallback_default_model
    model = requested_model or default_model
    allowed = policy["allowed_models"]
    if model not in allowed:
        raise ValueError(
            f"Model '{model}' is not allowed for compliance category '{profile.category}'"
        )
    return profile, model


def record_audit_event(project_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    event = {
        "project_id": project_id,
        "event_type": event_type,
        "payload": payload,
        "timestamp": _now_iso(),
    }
    return _STATE_BACKEND.add_audit_event(event)


def get_audit_events(project_id: str, limit: int = 100) -> list[dict[str, Any]]:
    return _STATE_BACKEND.list_audit_events(project_id=project_id, limit=limit)
