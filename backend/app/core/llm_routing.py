from dataclasses import dataclass
from typing import Any

from core.config import settings
from projects.registry import ProjectRegistry


@dataclass(frozen=True)
class ModelRoutingDecision:
    model: str
    routing_tier: str
    reason: str
    upsell_available: bool


def project_tier(project_id: str) -> str:
    if settings.DEPLOYMENT_MODE == "onprem":
        return "enterprise"
    record = ProjectRegistry().get(project_id)
    if record:
        return record.tier
    return settings.PROJECT_TIER.lower()


def select_model(
    *,
    project_id: str,
    requested_model: str | None,
    task_type: str,
    use_flagship: bool,
    compliance_required_model: str | None,
) -> ModelRoutingDecision:
    if compliance_required_model:
        return ModelRoutingDecision(
            model=compliance_required_model,
            routing_tier="compliance",
            reason="Compliance profile requires restricted model",
            upsell_available=False,
        )

    tier = project_tier(project_id)
    tier_rank = {"starter": 0, "pro": 1, "enterprise": 2}.get(tier, 0)

    if use_flagship and tier_rank >= 1:
        return ModelRoutingDecision(
            model=settings.FLAGSHIP_LLM_MODEL,
            routing_tier="flagship",
            reason="Explicit flagship request on pro+ tier",
            upsell_available=False,
        )

    if task_type == "reasoning" and tier_rank == 0:
        return ModelRoutingDecision(
            model=requested_model or settings.DEFAULT_LLM_MODEL,
            routing_tier="economy",
            reason="Reasoning task on starter tier uses economy model; upgrade to pro for flagship routing",
            upsell_available=True,
        )

    if task_type in {"reasoning", "extraction", "template"} and tier_rank >= 1:
        return ModelRoutingDecision(
            model=settings.FLAGSHIP_LLM_MODEL,
            routing_tier="flagship",
            reason=f"Automatic flagship routing for {task_type} on {tier} tier",
            upsell_available=False,
        )

    return ModelRoutingDecision(
        model=requested_model or settings.DEFAULT_LLM_MODEL,
        routing_tier="economy",
        reason="Default economy routing",
        upsell_available=tier_rank == 0,
    )


def routing_preview(project_id: str) -> dict[str, Any]:
    tier = project_tier(project_id)
    return {
        "project_id": project_id,
        "project_tier": tier,
        "economy_model": settings.DEFAULT_LLM_MODEL,
        "flagship_model": settings.FLAGSHIP_LLM_MODEL,
        "samples": {
            "general": select_model(
                project_id=project_id,
                requested_model=None,
                task_type="general",
                use_flagship=False,
                compliance_required_model=None,
            ).__dict__,
            "reasoning": select_model(
                project_id=project_id,
                requested_model=None,
                task_type="reasoning",
                use_flagship=False,
                compliance_required_model=None,
            ).__dict__,
            "reasoning_flagship": select_model(
                project_id=project_id,
                requested_model=None,
                task_type="reasoning",
                use_flagship=True,
                compliance_required_model=None,
            ).__dict__,
        },
    }
