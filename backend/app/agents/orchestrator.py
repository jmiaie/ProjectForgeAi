from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, TypedDict
from uuid import uuid4


class WorkflowState(TypedDict, total=False):
    project_id: str
    trace_id: str
    compliance: str
    status: str
    ingestion: dict[str, Any]
    graph_summary: dict[str, Any]
    templates: list[dict[str, Any]]
    current_stage: str
    states_visited: list[str]
    timeline: list[dict[str, Any]]


class OrchestrationStore:
    """In-memory workflow state persistence until DB layer is wired."""

    def __init__(self) -> None:
        self._by_project: dict[str, WorkflowState] = {}
        self._by_trace: dict[str, WorkflowState] = {}

    def save(self, state: WorkflowState) -> None:
        project_id = state["project_id"]
        trace_id = state["trace_id"]
        self._by_project[project_id] = state
        self._by_trace[trace_id] = state

    def get_project(self, project_id: str) -> WorkflowState | None:
        return self._by_project.get(project_id)

    def get_trace(self, trace_id: str) -> WorkflowState | None:
        return self._by_trace.get(trace_id)


class Orchestrator:
    def __init__(self, store: OrchestrationStore | None = None) -> None:
        self.store = store or OrchestrationStore()
        self._compiled_graph = self._build_langgraph()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat()

    def _append_state(self, state: WorkflowState, stage: str, details: dict[str, Any] | None = None) -> None:
        state.setdefault("states_visited", []).append(stage)
        state.setdefault("timeline", []).append(
            {"stage": stage, "timestamp": self._now_iso(), "details": details or {}}
        )
        state["current_stage"] = stage

    def _build_langgraph(self):
        try:
            from langgraph.graph import END, StateGraph
        except ImportError:
            return None

        graph = StateGraph(WorkflowState)
        graph.add_node("intake_complete", self._node_intake_complete)
        graph.add_node("ingestion_complete", self._node_ingestion_complete)
        graph.add_node("graph_built", self._node_graph_built)
        graph.add_node("templates_generated", self._node_templates_generated)

        graph.set_entry_point("intake_complete")
        graph.add_edge("intake_complete", "ingestion_complete")
        graph.add_edge("ingestion_complete", "graph_built")
        graph.add_edge("graph_built", "templates_generated")
        graph.add_edge("templates_generated", END)
        return graph.compile()

    def _node_intake_complete(self, state: WorkflowState) -> WorkflowState:
        self._append_state(state, "intake_complete", {"connected_integrations": []})
        state["status"] = "running"
        return state

    def _node_ingestion_complete(self, state: WorkflowState) -> WorkflowState:
        ingestion = state.get("ingestion") or {"status": "ingested", "files": 0, "chunks_indexed": 0, "details": []}
        self._append_state(
            state,
            "ingestion_complete",
            {"files": ingestion.get("files", 0), "chunks_indexed": ingestion.get("chunks_indexed", 0)},
        )
        state["ingestion"] = ingestion
        return state

    def _node_graph_built(self, state: WorkflowState) -> WorkflowState:
        ingestion = state.get("ingestion") or {}
        summary = {
            "nodes": ingestion.get("files", 0),
            "edges": max(0, ingestion.get("files", 0) - 1),
            "source": "phase2-placeholder",
        }
        state["graph_summary"] = summary
        self._append_state(state, "graph_built", summary)
        return state

    def _node_templates_generated(self, state: WorkflowState) -> WorkflowState:
        templates = [
            {"name": "project_charter", "status": "queued"},
            {"name": "risk_register", "status": "queued"},
            {"name": "weekly_status_report", "status": "queued"},
        ]
        state["templates"] = templates
        self._append_state(state, "templates_generated", {"count": len(templates)})
        state["status"] = "completed"
        return state

    async def run(
        self, project_id: str, compliance: str = "standard", ingestion: dict[str, Any] | None = None
    ) -> WorkflowState:
        state: WorkflowState = {
            "project_id": project_id,
            "trace_id": f"trace_{uuid4().hex[:12]}",
            "compliance": compliance,
            "status": "queued",
            "ingestion": ingestion or {"status": "ingested", "files": 0, "chunks_indexed": 0, "details": []},
            "states_visited": [],
            "timeline": [],
        }

        if self._compiled_graph is not None:
            result = self._compiled_graph.invoke(state)
            if isinstance(result, dict):
                state = result
        else:
            # Fallback execution preserves the same phase semantics without langgraph installed.
            state = self._node_intake_complete(state)
            state = self._node_ingestion_complete(state)
            state = self._node_graph_built(state)
            state = self._node_templates_generated(state)

        self.store.save(state)
        return state

    async def status(self, project_id: str) -> WorkflowState:
        state = self.store.get_project(project_id)
        if state:
            return state
        return {
            "project_id": project_id,
            "trace_id": "",
            "status": "not_found",
            "states_visited": [],
            "timeline": [],
            "current_stage": "unknown",
        }

    async def trace(self, trace_id: str) -> WorkflowState:
        state = self.store.get_trace(trace_id)
        if state:
            return state
        return {
            "project_id": "",
            "trace_id": trace_id,
            "status": "not_found",
            "states_visited": [],
            "timeline": [],
            "current_stage": "unknown",
        }
