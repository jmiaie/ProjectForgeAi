"""LangGraph-powered orchestrator agent.

The orchestrator runs a four-node state machine::

    retrieve_context  ->  plan  ->  dispatch_specialists  ->  finalize

When the optional ``langgraph`` dependency is installed we compile a real
``StateGraph``; otherwise we fall back to an equivalent linear coroutine so
the rest of the system (tests, frontend, CI) keeps working without it.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Iterable

from app.agents.specialists import DEFAULT_SPECIALISTS, SpecialistAgent
from app.agents.state import OrchestratorState, SpecialistOutput, empty_state
from app.compliance.enforcer import get_compliance_profile
from app.core.llm_router import LLMRequest, LLMRouter
from app.storage.locus_adapter import LocusAdapter
from app.storage.ompa_adapter import OmpaAdapter

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from langgraph.graph import END, StateGraph  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    StateGraph = None  # type: ignore[assignment]
    END = None  # type: ignore[assignment]


NodeFn = Callable[[OrchestratorState], Awaitable[OrchestratorState]]


class OrchestratorAgent:
    """Coordinates retrieval → planning → specialist fan-out → finalisation."""

    def __init__(
        self,
        llm_router: LLMRouter | None = None,
        specialists: dict[str, type[SpecialistAgent]] | None = None,
    ) -> None:
        self.llm_router = llm_router or LLMRouter()
        specialist_classes = specialists or DEFAULT_SPECIALISTS
        self.specialists: dict[str, SpecialistAgent] = {
            name: cls(llm_router=self.llm_router)
            for name, cls in specialist_classes.items()
        }

    # ------------------------------------------------------------------
    # Node implementations
    # ------------------------------------------------------------------
    async def retrieve_context(self, state: OrchestratorState) -> OrchestratorState:
        project_id = state["project_id"]
        objective = state.get("objective", "")
        locus = LocusAdapter(project_id)
        ompa = OmpaAdapter(project_id)

        await ompa.session_start()
        await ompa.record_decision(
            f"Orchestrator starting for objective: {objective}"
        )
        try:
            chunks = await locus.retrieve(objective, limit=8)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Locus retrieval failed: %s", exc)
            chunks = []
            warnings = list(state.get("warnings", []))
            warnings.append(f"context_retrieval_failed: {exc}")
            state = {**state, "warnings": warnings}

        profile = get_compliance_profile(project_id)
        return {
            **state,
            "context": chunks,
            "compliance_category": profile.category,
        }

    async def plan(self, state: OrchestratorState) -> OrchestratorState:
        existing = state.get("specialists")
        if existing:
            return {
                **state,
                "plan_raw": "(specialists provided by caller)",
                "plan": list(existing),
            }
        prompt = (
            "You are the ProjectForge AI orchestrator. "
            f"Compliance category: {state.get('compliance_category', 'standard')}. "
            f"Objective: {state.get('objective', '')}. "
            "List the specialist agents to invoke from this set: "
            f"{', '.join(self.specialists.keys())}. "
            "Output one specialist name per line, in execution order."
        )
        plan_text = await self.llm_router.call(
            LLMRequest(
                project_id=state["project_id"],
                task_type="reasoning",
                messages=[{"role": "user", "content": prompt}],
            )
        )
        chosen = self._select_specialists(plan_text)
        return {
            **state,
            "plan_raw": plan_text,
            "plan": chosen,
            "specialists": chosen,
        }

    def _select_specialists(self, plan_text: str) -> list[str]:
        candidates = []
        for line in plan_text.splitlines():
            token = line.strip(" -*\u2022\t0123456789.").lower()
            for name in self.specialists.keys():
                if name in token and name not in candidates:
                    candidates.append(name)
        if not candidates:
            candidates = list(self.specialists.keys())
        return candidates

    async def dispatch_specialists(
        self, state: OrchestratorState
    ) -> OrchestratorState:
        names = state.get("specialists") or list(self.specialists.keys())
        coros: list[Awaitable[SpecialistOutput]] = []
        ordered: list[str] = []
        for name in names:
            agent = self.specialists.get(name)
            if agent is None:
                continue
            ordered.append(name)
            coros.append(agent.run(state))

        results = await asyncio.gather(*coros, return_exceptions=True)
        outputs: dict[str, SpecialistOutput] = dict(state.get("outputs", {}))
        warnings = list(state.get("warnings", []))
        for name, result in zip(ordered, results):
            if isinstance(result, Exception):
                warnings.append(f"{name}_failed: {result}")
                outputs[name] = SpecialistOutput(
                    agent=name,
                    summary=f"Failed: {result}",
                    artefacts=[],
                    warnings=[str(result)],
                )
            else:
                outputs[name] = result

        return {**state, "outputs": outputs, "warnings": warnings}

    async def finalize(self, state: OrchestratorState) -> OrchestratorState:
        outputs = state.get("outputs", {})
        summary_lines = [
            f"- {name}: {out.get('summary', '')}" for name, out in outputs.items()
        ]
        final_summary = (
            "Orchestration complete.\n" + "\n".join(summary_lines)
            if summary_lines
            else "Orchestration complete with no specialist outputs."
        )

        ompa = OmpaAdapter(state["project_id"])
        await ompa.record_decision(final_summary)

        return {**state, "final_summary": final_summary}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def run(
        self,
        project_id: str,
        objective: str,
        specialists: Iterable[str] | None = None,
    ) -> OrchestratorState:
        state = empty_state(project_id, objective)
        if specialists is not None:
            state["specialists"] = list(specialists)

        compiled = self._compile_graph()
        if compiled is not None:
            return await compiled.ainvoke(state)
        return await self._run_linear(state)

    async def _run_linear(self, state: OrchestratorState) -> OrchestratorState:
        for node in (
            self.retrieve_context,
            self.plan,
            self.dispatch_specialists,
            self.finalize,
        ):
            state = await node(state)
        return state

    def _compile_graph(self) -> Any | None:
        if StateGraph is None or END is None:
            return None
        try:
            graph: Any = StateGraph(OrchestratorState)
            graph.add_node("retrieve_context", self.retrieve_context)
            graph.add_node("plan", self.plan)
            graph.add_node("dispatch_specialists", self.dispatch_specialists)
            graph.add_node("finalize", self.finalize)

            graph.set_entry_point("retrieve_context")
            graph.add_edge("retrieve_context", "plan")
            graph.add_edge("plan", "dispatch_specialists")
            graph.add_edge("dispatch_specialists", "finalize")
            graph.add_edge("finalize", END)
            return graph.compile()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("LangGraph compile failed (%s); using linear runner", exc)
            return None
