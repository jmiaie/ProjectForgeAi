from dataclasses import dataclass
from typing import Any

from compliance.enforcer import ComplianceEnforcer
from core.config import settings


FEATURE_CATALOG: dict[str, dict[str, Any]] = {
    "graph_enrichment_llm": {
        "tier": "pro",
        "description": "LLM-backed graph enrichment",
    },
    "langgraph_branching": {
        "tier": "pro",
        "description": "Conditional LangGraph orchestrator routing",
    },
    "temporal_schedules": {
        "tier": "enterprise",
        "description": "Temporal Schedule API sync",
    },
    "self_learning": {
        "tier": "enterprise",
        "description": "Self-improvement and adaptive project learning",
    },
    "rbac_enforcement": {
        "tier": "enterprise",
        "description": "Project-scoped RBAC enforcement",
    },
}

TIER_ORDER = {"starter": 0, "pro": 1, "enterprise": 2}


@dataclass(frozen=True)
class UpgradeDecision:
    allowed: bool
    feature: str
    reason: str
    project_tier: str
    required_tier: str
    compliance_allows_self_learning: bool


class UpgradeManager:
    def __init__(self, compliance: ComplianceEnforcer | None = None):
        self.compliance = compliance or ComplianceEnforcer()

    def project_tier(self) -> str:
        deployment = settings.DEPLOYMENT_MODE
        if deployment == "onprem":
            return "enterprise"
        if settings.PROJECT_TIER:
            return settings.PROJECT_TIER.lower()
        return "starter"

    def feature_status(self, project_id: str) -> dict[str, Any]:
        profile = self.compliance.get_profile(project_id)
        tier = self.project_tier()
        features = {}
        for feature, meta in FEATURE_CATALOG.items():
            required = meta["tier"]
            enabled = TIER_ORDER[tier] >= TIER_ORDER[required]
            if feature == "self_learning":
                enabled = enabled and profile.allow_self_learning
            if feature == "rbac_enforcement":
                enabled = enabled and settings.RBAC_ENFORCE
            features[feature] = {
                "enabled": enabled,
                "required_tier": required,
                "description": meta["description"],
            }
        return {
            "project_id": project_id,
            "deployment_mode": settings.DEPLOYMENT_MODE,
            "project_tier": tier,
            "compliance_category": profile.category,
            "allow_self_learning": profile.allow_self_learning,
            "features": features,
        }

    def check_feature(self, project_id: str, feature: str) -> UpgradeDecision:
        meta = FEATURE_CATALOG.get(feature)
        if meta is None:
            return UpgradeDecision(
                allowed=False,
                feature=feature,
                reason=f"Unknown feature: {feature}",
                project_tier=self.project_tier(),
                required_tier="unknown",
                compliance_allows_self_learning=False,
            )

        tier = self.project_tier()
        required = meta["tier"]
        allowed = TIER_ORDER[tier] >= TIER_ORDER[required]
        reason = "Feature enabled for project tier"

        profile = self.compliance.get_profile(project_id)
        compliance_allows = profile.allow_self_learning
        if feature == "self_learning":
            allowed = allowed and compliance_allows
            if not compliance_allows:
                reason = f"{profile.category} profile blocks self-learning"
            elif not allowed:
                reason = f"Requires {required} tier (current: {tier})"
        elif not allowed:
            reason = f"Requires {required} tier (current: {tier})"

        return UpgradeDecision(
            allowed=allowed,
            feature=feature,
            reason=reason,
            project_tier=tier,
            required_tier=required,
            compliance_allows_self_learning=compliance_allows,
        )

    def require_feature(self, project_id: str, feature: str) -> UpgradeDecision:
        decision = self.check_feature(project_id, feature)
        if not decision.allowed:
            raise PermissionError(decision.reason)
        return decision
