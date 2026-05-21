"""Stub orchestrator for API integration tests (no live LLM calls)."""

from __future__ import annotations

from typing import Any

from app.agents.specialists import DEFAULT_SPECIALISTS
from app.agents.state import OrchestratorState, SpecialistOutput


def _output(
    agent: str,
    summary: str,
    artefacts: list[dict[str, Any]],
) -> SpecialistOutput:
    return SpecialistOutput(
        agent=agent,
        summary=summary,
        artefacts=artefacts,
        warnings=[],
    )


class StubOrchestrator:
    """Minimal orchestrator that returns graph-friendly artefacts."""

    def __init__(self) -> None:
        self.specialists = dict.fromkeys(DEFAULT_SPECIALISTS.keys())

    async def run(
        self,
        project_id: str,
        objective: str = "",
        specialists: list[str] | None = None,
        **_: Any,
    ) -> OrchestratorState:
        plan = specialists or list(DEFAULT_SPECIALISTS.keys())[:3]
        outputs: dict[str, SpecialistOutput] = {
            "schedule": _output(
                "schedule",
                "Stub schedule plan",
                [{"kind": "milestone", "value": "Kickoff complete"}],
            ),
            "compliance": _output(
                "compliance",
                "Stub compliance review",
                [{"kind": "compliance_control", "value": "SOC2 access logging"}],
            ),
            "risk": _output(
                "risk",
                "Stub risk scan",
                [{"kind": "risk", "value": "Vendor dependency delay"}],
            ),
        }
        invoked = [name for name in plan if name in outputs] or list(outputs.keys())
        return {
            "project_id": project_id,
            "objective": objective,
            "compliance_category": "standard",
            "plan": invoked,
            "context": [],
            "outputs": {k: outputs[k] for k in invoked},
            "final_summary": "Stub orchestration complete (test mode).",
            "warnings": [],
        }
