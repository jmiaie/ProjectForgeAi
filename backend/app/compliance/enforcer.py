"""Compliance profile lookup and enforcement helpers.

In production this module would consult a database of per-project compliance
selections (HIPAA, SOC 2, GDPR, legal hold, etc.). For the v14 scaffold we
expose a lightweight in-memory registry so the rest of the system can call
``get_compliance_profile`` deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ComplianceCategory = Literal["standard", "hipaa", "soc2", "gdpr", "legal"]


@dataclass(frozen=True)
class ComplianceProfile:
    """A single project's compliance posture."""

    project_id: str
    category: ComplianceCategory = "standard"
    require_audit_log: bool = False
    forbid_external_llms: bool = False
    allowed_models: tuple[str, ...] = field(default_factory=tuple)


_PROFILES: dict[str, ComplianceProfile] = {}


def set_compliance_profile(profile: ComplianceProfile) -> None:
    """Register or overwrite the compliance profile for a project."""

    _PROFILES[profile.project_id] = profile


def get_compliance_profile(project_id: str) -> ComplianceProfile:
    """Return the compliance profile for ``project_id`` (default: standard)."""

    return _PROFILES.get(project_id, ComplianceProfile(project_id=project_id))


def is_self_improvement_allowed(project_id: str) -> bool:
    """Self-learning / self-healing is gated for regulated categories."""

    profile = get_compliance_profile(project_id)
    return profile.category in {"standard"}
