from typing import Any, Literal, TypedDict

from agents.state import AgentStep, OrchestratorRun, OrchestratorStatus

BranchPath = Literal["standard", "compliance_first", "risk_heavy"]

BRANCH_SEQUENCES: dict[BranchPath, list[str]] = {
    "standard": ["scheduler", "risk_analyst", "compliance_reviewer", "template_generator"],
    "compliance_first": [
        "compliance_reviewer",
        "scheduler",
        "risk_analyst",
        "template_generator",
    ],
    "risk_heavy": ["risk_analyst", "scheduler", "compliance_reviewer", "template_generator"],
}

COMPLIANCE_GOAL_KEYWORDS = ("compliance", "hipaa", "legal", "gdpr", "soc2", "phi", "pii")


class OrchestratorGraphState(TypedDict, total=False):
    project_id: str
    goal: str
    run_id: str
    steps: list[dict[str, Any]]
    warnings: list[str]
    branch_path: BranchPath


def decide_branch_path(goal: str, intake_output: dict[str, Any]) -> BranchPath:
    goal_lower = goal.lower()
    if any(keyword in goal_lower for keyword in COMPLIANCE_GOAL_KEYWORDS):
        return "compliance_first"

    node_count = int(intake_output.get("graph_node_count", 0) or 0)
    context_items = int(intake_output.get("context_items", 0) or 0)
    if node_count <= 1 and context_items == 0:
        return "risk_heavy"

    return "standard"


def intake_output_from_steps(steps: list[dict[str, Any]]) -> dict[str, Any]:
    for step in reversed(steps):
        if step.get("name") == "intake_analyst":
            return step.get("output", {})
    return {}


def build_orchestrator_graph(agent, sequence: list[str] | None = None, *, branching: bool = False):
    from langgraph.graph import END, StateGraph

    graph = StateGraph(OrchestratorGraphState)

    def make_node(agent_name: str):
        async def node(state: OrchestratorGraphState, config) -> dict[str, Any]:
            tools = config["configurable"]["tools"]
            step = await agent._run_agent_step(agent_name, state["goal"], tools)
            warnings = list(state.get("warnings", []))
            if step.output.get("warning"):
                warnings.append(step.output["warning"])
            steps = list(state.get("steps", []))
            steps.append(step.model_dump(mode="python"))
            updates: dict[str, Any] = {"steps": steps, "warnings": warnings}
            if agent_name == "intake_analyst" and branching:
                updates["branch_path"] = decide_branch_path(state["goal"], step.output)
            return updates

        return node

    if branching:
        graph.add_node("intake_analyst", make_node("intake_analyst"))

        async def run_branch_specialists(state: OrchestratorGraphState, config) -> dict[str, Any]:
            tools = config["configurable"]["tools"]
            path = state.get("branch_path") or decide_branch_path(
                state.get("goal", ""),
                intake_output_from_steps(state.get("steps", [])),
            )
            steps = list(state.get("steps", []))
            warnings = list(state.get("warnings", []))
            for agent_name in BRANCH_SEQUENCES[path]:
                step = await agent._run_agent_step(agent_name, state["goal"], tools)
                if step.output.get("warning"):
                    warnings.append(step.output["warning"])
                steps.append(step.model_dump(mode="python"))
            return {"steps": steps, "warnings": warnings, "branch_path": path}

        graph.add_node("run_branch_specialists", run_branch_specialists)
        graph.set_entry_point("intake_analyst")
        graph.add_edge("intake_analyst", "run_branch_specialists")
        graph.add_edge("run_branch_specialists", END)
        return graph.compile()

    if not sequence:
        sequence = ["intake_analyst"]

    for index, agent_name in enumerate(sequence):
        graph.add_node(agent_name, make_node(agent_name))
        if index == 0:
            graph.set_entry_point(agent_name)
        else:
            graph.add_edge(sequence[index - 1], agent_name)

    graph.add_edge(sequence[-1], END)
    return graph.compile()


async def run_langgraph_orchestrator(
    agent,
    run: OrchestratorRun,
    sequence: list[str],
    tools,
    checkpoint_writer,
    *,
    branching: bool = False,
) -> OrchestratorRun:
    compiled = build_orchestrator_graph(agent, sequence, branching=branching)
    initial_state: OrchestratorGraphState = {
        "project_id": run.project_id,
        "goal": run.goal,
        "run_id": run.run_id,
        "steps": [step.model_dump(mode="python") for step in run.steps],
        "warnings": list(run.warnings),
    }

    final_state = await compiled.ainvoke(
        initial_state,
        config={"configurable": {"tools": tools}},
    )

    run.steps = [AgentStep.model_validate(step) for step in final_state.get("steps", [])]
    run.warnings = final_state.get("warnings", [])
    if final_state.get("branch_path"):
        run.metadata = {**(run.metadata or {}), "branch_path": final_state["branch_path"]}
    run.status = OrchestratorStatus.RUNNING
    checkpoint_writer(run)
    return run
