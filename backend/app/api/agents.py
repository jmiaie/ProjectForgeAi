"""Agent orchestration HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.agents.orchestrator import OrchestratorAgent

router = APIRouter(prefix="/agents", tags=["agents"])


def get_orchestrator() -> OrchestratorAgent:
    return OrchestratorAgent()


class OrchestrateRequest(BaseModel):
    project_id: str
    objective: str
    specialists: list[str] | None = Field(
        default=None,
        description=(
            "Optional explicit list of specialist names to invoke. When omitted "
            "the orchestrator will plan the set itself."
        ),
    )


@router.post("/orchestrate")
async def orchestrate(
    payload: OrchestrateRequest,
    orchestrator: OrchestratorAgent = Depends(get_orchestrator),
) -> dict[str, Any]:
    state = await orchestrator.run(
        project_id=payload.project_id,
        objective=payload.objective,
        specialists=payload.specialists,
    )
    return {
        "project_id": state.get("project_id"),
        "objective": state.get("objective"),
        "compliance_category": state.get("compliance_category"),
        "plan": state.get("plan"),
        "specialists_invoked": list(state.get("outputs", {}).keys()),
        "outputs": state.get("outputs", {}),
        "final_summary": state.get("final_summary"),
        "warnings": state.get("warnings", []),
    }


@router.get("/specialists")
async def list_specialists(
    orchestrator: OrchestratorAgent = Depends(get_orchestrator),
) -> dict[str, Any]:
    return {"specialists": list(orchestrator.specialists.keys())}
