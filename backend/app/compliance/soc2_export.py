from datetime import UTC, datetime
from typing import Any

from agents.audit import OrchestratorAuditStore
from compliance.audit import ComplianceAuditStore
from compliance.enforcer import ComplianceEnforcer
from core.config import settings
from core.rbac import RBACService


SOC2_CONTROLS: list[dict[str, str]] = [
    {"id": "CC1.1", "title": "Control environment and governance", "category": "Common Criteria"},
    {"id": "CC6.1", "title": "Logical access security", "category": "Common Criteria"},
    {"id": "CC6.2", "title": "Authentication mechanisms", "category": "Common Criteria"},
    {"id": "CC6.3", "title": "Access removal and role changes", "category": "Common Criteria"},
    {"id": "CC7.2", "title": "Security event monitoring", "category": "Common Criteria"},
    {"id": "CC8.1", "title": "Change management", "category": "Common Criteria"},
]


class SOC2ExportService:
    def __init__(
        self,
        compliance: ComplianceEnforcer | None = None,
        rbac: RBACService | None = None,
        compliance_audit: ComplianceAuditStore | None = None,
        orchestrator_audit: OrchestratorAuditStore | None = None,
    ):
        self.compliance = compliance or ComplianceEnforcer()
        self.rbac = rbac or RBACService()
        self.compliance_audit = compliance_audit or ComplianceAuditStore()
        self.orchestrator_audit = orchestrator_audit or OrchestratorAuditStore()

    def export_project(self, project_id: str, limit: int = 500) -> dict[str, Any]:
        profile = self.compliance.get_profile(project_id).as_dict()
        compliance_events = self.compliance_audit.list_events(project_id, limit=limit)
        orchestrator_events = self.orchestrator_audit.list_events(project_id, limit=limit)
        members = self.rbac.list_members(project_id)

        denied_events = [event for event in compliance_events if not event.get("allowed")]
        profile_changes = [event for event in compliance_events if event.get("action") == "profile_set"]
        external_writes = [event for event in compliance_events if event.get("action") == "external_write"]

        controls = [
            self._control_cc11(project_id, profile),
            self._control_cc61(project_id, members),
            self._control_cc62(),
            self._control_cc63(members),
            self._control_cc72(compliance_events, orchestrator_events, denied_events),
            self._control_cc81(profile_changes, external_writes),
        ]

        return {
            "project_id": project_id,
            "framework": "SOC 2 Type II (starter mapping)",
            "generated_at": datetime.now(UTC).isoformat(),
            "profile": profile,
            "summary": {
                "control_count": len(controls),
                "implemented": sum(1 for control in controls if control["status"] == "implemented"),
                "partial": sum(1 for control in controls if control["status"] == "partial"),
                "compliance_events": len(compliance_events),
                "orchestrator_events": len(orchestrator_events),
                "denied_actions": len(denied_events),
                "members": len(members),
            },
            "controls": controls,
        }

    def _control_cc11(self, project_id: str, profile: dict[str, Any]) -> dict[str, Any]:
        evidence = [
            {"type": "compliance_profile", "category": profile.get("category"), "audit_required": profile.get("audit_required")},
            {
                "type": "policy_flags",
                "allow_self_learning": profile.get("allow_self_learning"),
                "require_human_approval_for_external_writes": profile.get("require_human_approval_for_external_writes"),
            },
        ]
        status = "implemented" if profile.get("audit_required") else "partial"
        return self._control("CC1.1", status, evidence)

    def _control_cc61(self, project_id: str, members: list[dict[str, Any]]) -> dict[str, Any]:
        evidence = [
            {"type": "rbac_enforce", "enabled": settings.RBAC_ENFORCE},
            {"type": "member_count", "count": len(members)},
            {"type": "members", "records": members[:20]},
        ]
        status = "implemented" if settings.RBAC_ENFORCE and members else "partial"
        return self._control("CC6.1", status, evidence)

    def _control_cc62(self) -> dict[str, Any]:
        evidence = [
            {
                "type": "oidc",
                "enabled": settings.OIDC_ENABLED,
                "mock_mode": settings.OIDC_MOCK,
                "issuer": settings.OIDC_ISSUER,
            },
            {"type": "session_ttl_seconds", "value": settings.AUTH_SESSION_TTL_SECONDS},
        ]
        status = "implemented" if settings.OIDC_ENABLED and not settings.OIDC_MOCK else "partial"
        return self._control("CC6.2", status, evidence)

    def _control_cc63(self, members: list[dict[str, Any]]) -> dict[str, Any]:
        evidence = [{"type": "membership_updates", "records": members[:20]}]
        status = "implemented" if members else "partial"
        return self._control("CC6.3", status, evidence)

    def _control_cc72(
        self,
        compliance_events: list[dict[str, Any]],
        orchestrator_events: list[dict[str, Any]],
        denied_events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        evidence = [
            {"type": "compliance_audit_count", "count": len(compliance_events)},
            {"type": "orchestrator_audit_count", "count": len(orchestrator_events)},
            {"type": "denied_actions", "count": len(denied_events), "samples": denied_events[:5]},
        ]
        status = "implemented" if compliance_events or orchestrator_events else "partial"
        return self._control("CC7.2", status, evidence)

    def _control_cc81(
        self,
        profile_changes: list[dict[str, Any]],
        external_writes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        evidence = [
            {"type": "profile_changes", "count": len(profile_changes), "samples": profile_changes[:5]},
            {"type": "external_writes", "count": len(external_writes), "samples": external_writes[:5]},
        ]
        status = "implemented" if profile_changes or external_writes else "partial"
        return self._control("CC8.1", status, evidence)

    def _control(self, control_id: str, status: str, evidence: list[dict[str, Any]]) -> dict[str, Any]:
        meta = next(item for item in SOC2_CONTROLS if item["id"] == control_id)
        return {
            "control_id": control_id,
            "title": meta["title"],
            "category": meta["category"],
            "status": status,
            "evidence": evidence,
        }
