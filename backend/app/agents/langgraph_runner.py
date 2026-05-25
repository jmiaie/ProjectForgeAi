from typing import Any, TypedDict

from agents.state import AgentStep, OrchestratorRun, OrchestratorStatus


class OrchestratorGraphState(TypedDict, total=False):
    project_id: str
    goal: str
    run_id: str
    steps: list[dict[str, Any]]
    warnings: list[str]


def build_orchestrator_graph(agent, sequence: list[str]):
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
            return {"steps": steps, "warnings": warnings}

        return node

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
) -> OrchestratorRun:
    compiled = build_orchestrator_graph(agent, sequence)
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
    run.status = OrchestratorStatus.RUNNING
    checkpoint_writer(run)
    return run
