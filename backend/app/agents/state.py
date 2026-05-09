"""Typed state passed between orchestrator nodes.

The structure is deliberately ``TypedDict`` so it is friendly both to LangGraph
(which requires a typed state for ``StateGraph``) and to the synchronous
fallback path used when LangGraph is not installed.
"""

from __future__ import annotations

from typing import Any, TypedDict


class SpecialistOutput(TypedDict, total=False):
    """Structured artefact produced by a specialist agent."""

    agent: str
    summary: str
    artefacts: list[dict[str, Any]]
    warnings: list[str]


class OrchestratorState(TypedDict, total=False):
    """Mutable state flowing through the orchestrator graph."""

    project_id: str
    objective: str
    compliance_category: str
    context: list[dict[str, Any]]
    plan: list[str]
    plan_raw: str
    specialists: list[str]
    outputs: dict[str, SpecialistOutput]
    final_summary: str
    warnings: list[str]


def empty_state(project_id: str, objective: str) -> OrchestratorState:
    """Return a fresh orchestrator state with sensible defaults."""

    return OrchestratorState(
        project_id=project_id,
        objective=objective,
        compliance_category="standard",
        context=[],
        plan=[],
        plan_raw="",
        specialists=[],
        outputs={},
        final_summary="",
        warnings=[],
    )
