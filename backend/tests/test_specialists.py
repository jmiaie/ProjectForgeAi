"""Unit tests for individual specialist agents."""

from __future__ import annotations

from typing import Any

import pytest

from app.agents.specialists import (
    CommsAgent,
    ComplianceAgent,
    ContractsAgent,
    RiskAgent,
    ScheduleAgent,
)
from app.agents.state import empty_state


class StubLLMRouter:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[Any] = []

    async def call(self, req: Any) -> str:
        self.calls.append(req)
        return self.response


@pytest.mark.asyncio
async def test_schedule_agent_parses_milestones_and_tasks() -> None:
    response = (
        "Milestone: Kickoff complete (duration: 5d)\n"
        "Milestone: Design review (duration: 10d)\n"
        "Task: Draft scope (depends on: kickoff)\n"
    )
    agent = ScheduleAgent(llm_router=StubLLMRouter(response))
    output = await agent.run(empty_state("p1", "Build foundation"))
    kinds = {a["kind"] for a in output["artefacts"]}
    assert kinds == {"milestone", "task"}
    assert "milestone" in output["summary"]


@pytest.mark.asyncio
async def test_comms_agent_splits_three_templates() -> None:
    response = "Kickoff body\n---\nWeekly status body\n---\nEscalation body"
    agent = CommsAgent(llm_router=StubLLMRouter(response))
    output = await agent.run(empty_state("p1", "Launch"))
    labels = [a["label"] for a in output["artefacts"]]
    assert labels[:3] == ["kickoff_email", "status_update", "escalation"]


@pytest.mark.asyncio
async def test_contracts_agent_labels_known_types() -> None:
    response = (
        "SOW: scope of work template body\n"
        "===\n"
        "MSA: master services template body\n"
        "===\n"
        "NDA: nondisclosure template body"
    )
    agent = ContractsAgent(llm_router=StubLLMRouter(response))
    output = await agent.run(empty_state("p1", "Vendor onboarding"))
    labels = [a["label"] for a in output["artefacts"]]
    assert labels == ["sow", "msa", "nda"]


@pytest.mark.asyncio
async def test_compliance_agent_falls_back_to_baseline_controls() -> None:
    agent = ComplianceAgent(llm_router=StubLLMRouter("(no controls returned)"))
    state = empty_state("p1", "Health system rollout")
    state["compliance_category"] = "hipaa"
    output = await agent.run(state)
    assert output["artefacts"], "should produce baseline controls when LLM omits them"
    assert all(a["category"] == "hipaa" for a in output["artefacts"])


@pytest.mark.asyncio
async def test_risk_agent_extracts_risk_lines() -> None:
    response = (
        "Risk: Vendor delay | Likelihood: medium | Impact: high | Mitigation: "
        "pre-contract penalty\n"
        "Risk: Scope creep | Likelihood: high | Impact: medium | Mitigation: "
        "weekly change board"
    )
    agent = RiskAgent(llm_router=StubLLMRouter(response))
    output = await agent.run(empty_state("p1", "Replatform"))
    assert len(output["artefacts"]) == 2
    assert all(a["kind"] == "risk" for a in output["artefacts"])
