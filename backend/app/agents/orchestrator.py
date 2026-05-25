from typing import Any

from agents.langgraph_runner import run_langgraph_orchestrator
from agents.run_store import OrchestratorRunStore
from agents.state import AgentStep, OrchestratorRequest, OrchestratorRun, OrchestratorStatus
from agents.tools import OrchestratorToolContext
from core.config import settings


DEFAULT_AGENT_SEQUENCE = [
    "intake_analyst",
    "scheduler",
    "risk_analyst",
    "compliance_reviewer",
    "template_generator",
]


class OrchestratorAgent:
    def __init__(
        self,
        run_store: OrchestratorRunStore | None = None,
        tool_context_factory=None,
    ):
        self.run_store = run_store or OrchestratorRunStore()
        self.tool_context_factory = tool_context_factory or (
            lambda project_id: OrchestratorToolContext(project_id)
        )

    async def run(self, request: OrchestratorRequest) -> dict:
        sequence = request.requested_agents or DEFAULT_AGENT_SEQUENCE
        run = self._load_or_create_run(request)

        if request.resume and run.steps:
            completed = {step.name for step in run.steps if step.status == OrchestratorStatus.COMPLETED}
            sequence = [name for name in sequence if name not in completed]

        tools = self.tool_context_factory(request.project_id)

        if settings.USE_LANGGRAPH_ORCHESTRATOR:
            run = await run_langgraph_orchestrator(
                self,
                run,
                sequence,
                tools,
                self.run_store.write_checkpoint,
            )
        else:
            for agent_name in sequence:
                step = await self._run_agent_step(agent_name, request.goal, tools)
                run.steps.append(step)
                if step.output.get("warning"):
                    run.warnings.append(step.output["warning"])
                self.run_store.write_checkpoint(run)

        await tools.record_decision(
            f"Orchestrator {run.run_id} completed {len(run.steps)} steps for {request.project_id}: {request.goal}"
        )
        run.artifacts = self._compile_artifacts(run)
        run.complete()
        return self.run_store.write(run)

    def status(self, project_id: str, run_id: str | None = None) -> dict[str, Any]:
        run = self.run_store.read(project_id, run_id)
        if run is None:
            return {
                "project_id": project_id,
                "run_id": run_id,
                "status": "missing",
                "warnings": [f"{project_id}: no orchestrator run found"],
            }
        return run

    def list_runs(self, project_id: str, limit: int = 20) -> dict[str, Any]:
        return {"project_id": project_id, "runs": self.run_store.list_runs(project_id, limit)}

    def _load_or_create_run(self, request: OrchestratorRequest) -> OrchestratorRun:
        if request.run_id:
            existing = self.run_store.read(request.project_id, request.run_id)
            if existing and request.resume:
                payload = {key: value for key, value in existing.items() if key != "path"}
                run = OrchestratorRun.model_validate(payload)
                run.status = OrchestratorStatus.RUNNING
                return run

        run = OrchestratorRun(project_id=request.project_id, goal=request.goal)
        if request.run_id:
            run.run_id = request.run_id
        return run

    async def _run_agent_step(
        self,
        agent_name: str,
        goal: str,
        tools: OrchestratorToolContext,
    ) -> AgentStep:
        handlers = {
            "intake_analyst": self._intake_analyst,
            "scheduler": self._scheduler,
            "risk_analyst": self._risk_analyst,
            "compliance_reviewer": self._compliance_reviewer,
            "template_generator": self._template_generator,
        }
        handler = handlers.get(agent_name, self._generic_agent)
        output = await handler(goal, tools)
        summary = output.pop("summary")
        await tools.record_decision(f"{agent_name}: {summary}")
        return AgentStep(
            name=agent_name,
            status=OrchestratorStatus.COMPLETED,
            summary=summary,
            output=output,
        )

    async def _intake_analyst(self, goal: str, tools: OrchestratorToolContext) -> dict:
        graph = await tools.graph_snapshot()
        context = await tools.retrieve_context(goal)
        return {
            "summary": (
                f"Reviewed graph with {graph['node_count']} nodes and {len(context)} retrieved context items."
            ),
            "graph_node_count": graph["node_count"],
            "graph_edge_count": graph["edge_count"],
            "context_items": len(context),
            "sources": _sources_from_graph(graph),
        }

    async def _scheduler(self, goal: str, tools: OrchestratorToolContext) -> dict:
        graph = await tools.graph_snapshot()
        document_count = _count_label(graph, "Document")
        milestone_seed = max(1, document_count)
        return {
            "summary": f"Created starter schedule outline with {milestone_seed} milestone seed(s).",
            "milestones": [
                {"name": "Kickoff and source validation", "sequence": 1},
                {"name": "Baseline plan generation", "sequence": 2},
                {"name": "Review and approval loop", "sequence": 3},
            ],
        }

    async def _risk_analyst(self, goal: str, tools: OrchestratorToolContext) -> dict:
        graph = await tools.graph_snapshot()
        warnings = graph.get("warnings", [])
        risks = [
            {
                "name": "Source extraction warnings",
                "severity": "medium",
                "evidence": warnings,
            }
        ] if warnings else [
            {
                "name": "Pending stakeholder validation",
                "severity": "low",
                "evidence": ["Graph is starter-level until stakeholder/task extraction is enabled."],
            }
        ]
        return {"summary": f"Identified {len(risks)} starter risk item(s).", "risks": risks}

    async def _compliance_reviewer(self, goal: str, tools: OrchestratorToolContext) -> dict:
        storage = tools.storage_status()
        profile = tools.compliance_profile()
        return {
            "summary": "Checked storage and graph backends for compliance gating readiness.",
            "profile": profile,
            "storage": storage,
            "controls": [
                "Keep self-learning gated by compliance profile.",
                "Preserve source hash provenance on generated outputs.",
                "Require human approval before external integration writes.",
            ],
        }

    async def _template_generator(self, goal: str, tools: OrchestratorToolContext) -> dict:
        integrations = await tools.recommended_integrations()
        return {
            "summary": "Prepared starter project operating templates.",
            "templates": [
                "Project charter",
                "Stakeholder register",
                "Risk register",
                "Weekly status report",
                "Decision log",
            ],
            "recommended_integrations": integrations,
        }

    async def _generic_agent(self, goal: str, tools: OrchestratorToolContext) -> dict:
        return {
            "summary": f"Recorded placeholder output for custom agent against goal: {goal}",
            "warning": "Custom agent has no registered handler yet.",
        }

    def _compile_artifacts(self, run: OrchestratorRun) -> dict[str, Any]:
        return {
            "project_operating_plan": {
                "goal": run.goal,
                "sections": [step.name for step in run.steps],
                "next_actions": [
                    "Validate extracted sources with project owner.",
                    "Run LLM fact extraction into stakeholder/task/risk graph nodes.",
                    "Generate first project charter from graph provenance.",
                ],
            }
        }


def _count_label(graph: dict[str, Any], label: str) -> int:
    return sum(1 for node in graph.get("graph", {}).get("nodes", []) if node.get("label") == label)


def _sources_from_graph(graph: dict[str, Any]) -> list[str]:
    sources = []
    for node in graph.get("graph", {}).get("nodes", []):
        properties = node.get("properties", {})
        if node.get("label") == "Document" and properties.get("source"):
            sources.append(properties["source"])
    return sources
