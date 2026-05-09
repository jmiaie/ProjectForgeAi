"""Orchestrator agent skeleton.

The full orchestrator is implemented as a LangGraph state machine that fans
out to specialist agents (scheduling, comms, contracts, compliance, ...).
This scaffold defines the public surface and a synchronous fallback that
mirrors the eventual graph so other modules can wire against it today.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.compliance.enforcer import get_compliance_profile
from app.core.llm_router import LLMRequest, LLMRouter
from app.storage.locus_adapter import LocusAdapter
from app.storage.ompa_adapter import OmpaAdapter

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorState:
    project_id: str
    objective: str
    context: list[dict[str, Any]] = field(default_factory=list)
    plan: list[str] = field(default_factory=list)
    outputs: dict[str, Any] = field(default_factory=dict)


class OrchestratorAgent:
    """Coordinates retrieval, planning and specialist hand-off."""

    def __init__(self, llm_router: LLMRouter | None = None) -> None:
        self.llm_router = llm_router or LLMRouter()

    async def run(self, project_id: str, objective: str) -> OrchestratorState:
        state = OrchestratorState(project_id=project_id, objective=objective)
        locus = LocusAdapter(project_id)
        ompa = OmpaAdapter(project_id)

        state.context = await locus.retrieve(objective, limit=8)
        await ompa.record_decision(f"Orchestrator launched for objective: {objective}")

        profile = get_compliance_profile(project_id)
        plan_prompt = (
            "You are the ProjectForge AI orchestrator. "
            f"Compliance category: {profile.category}. Objective: {objective}. "
            "Produce a numbered plan of specialist agents to invoke."
        )
        plan_text = await self.llm_router.call(
            LLMRequest(
                project_id=project_id,
                task_type="reasoning",
                messages=[{"role": "user", "content": plan_prompt}],
            )
        )
        state.plan = [
            line.strip(" -*0123456789.")
            for line in plan_text.splitlines()
            if line.strip()
        ]
        state.outputs["plan_raw"] = plan_text
        return state
