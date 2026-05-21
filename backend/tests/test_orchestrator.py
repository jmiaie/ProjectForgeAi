"""Tests for the orchestrator graph and the /agents API."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.agents.orchestrator import OrchestratorAgent
from app.agents.specialists.base import SpecialistAgent
from app.agents.state import OrchestratorState, SpecialistOutput
from app.main import app


class _FakeSpecialist(SpecialistAgent):
    name = "fake"

    def __init__(self, llm_router: Any = None, label: str = "fake") -> None:
        super().__init__(llm_router=llm_router)
        self.label = label
        self.name = label

    def system_prompt(self, state: OrchestratorState) -> str:  # pragma: no cover
        return ""

    async def run(self, state: OrchestratorState) -> SpecialistOutput:
        return SpecialistOutput(
            agent=self.label,
            summary=f"{self.label} ran for {state.get('objective')}",
            artefacts=[{"kind": self.label, "value": "ok"}],
            warnings=[],
        )


class _StubLLMRouter:
    async def call(self, req: Any) -> str:
        return "alpha\nbeta\n"


def _make_orchestrator() -> OrchestratorAgent:
    orch = OrchestratorAgent(
        llm_router=_StubLLMRouter(),
        specialists={"alpha": _FakeSpecialist, "beta": _FakeSpecialist},
    )
    orch.specialists["alpha"].name = "alpha"
    orch.specialists["alpha"].label = "alpha"  # type: ignore[attr-defined]
    orch.specialists["beta"].name = "beta"
    orch.specialists["beta"].label = "beta"  # type: ignore[attr-defined]
    return orch


@pytest.mark.asyncio
async def test_orchestrator_runs_planned_specialists() -> None:
    orch = _make_orchestrator()
    state = await orch.run(project_id="p1", objective="Launch product")
    assert state["plan"] == ["alpha", "beta"]
    outputs = state["outputs"]
    assert set(outputs.keys()) == {"alpha", "beta"}
    assert "Orchestration complete" in state["final_summary"]


@pytest.mark.asyncio
async def test_orchestrator_honours_explicit_specialist_list() -> None:
    orch = _make_orchestrator()
    state = await orch.run(
        project_id="p1", objective="Launch product", specialists=["beta"]
    )
    assert list(state["outputs"].keys()) == ["beta"]


def test_agents_orchestrate_endpoint() -> None:
    client = TestClient(app)
    res = client.post(
        "/api/v1/agents/orchestrate",
        json={"project_id": "p1", "objective": "Spin up new project"},
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["project_id"] == "p1"
    assert isinstance(payload["specialists_invoked"], list)
    assert payload["final_summary"]


def test_list_specialists_endpoint() -> None:
    client = TestClient(app)
    res = client.get("/api/v1/agents/specialists")
    assert res.status_code == 200
    names = res.json()["specialists"]
    assert {"schedule", "comms", "contracts", "compliance", "risk"}.issubset(names)
