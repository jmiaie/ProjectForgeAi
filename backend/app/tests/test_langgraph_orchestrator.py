import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.langgraph_runner import build_orchestrator_graph
from agents.orchestrator import OrchestratorAgent
from agents.run_store import OrchestratorRunStore
from agents.state import OrchestratorRequest
from core.config import settings


class LangGraphOrchestratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_langgraph_runner_produces_same_step_count(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = OrchestratorRunStore(root=str(Path(temp_dir) / "runs"))
            agent = OrchestratorAgent(
                run_store=store,
                tool_context_factory=lambda project_id: _FakeToolContext(project_id),
            )
            with patch.object(settings, "USE_LANGGRAPH_ORCHESTRATOR", True):
                result = await agent.run(
                    OrchestratorRequest(project_id="lg", goal="LangGraph test", run_id="run_lg")
                )
            self.assertEqual(result["status"], "completed")
            self.assertEqual(len(result["steps"]), 5)

    def test_build_orchestrator_graph_compiles(self):
        agent = OrchestratorAgent(tool_context_factory=lambda project_id: _FakeToolContext(project_id))
        compiled = build_orchestrator_graph(agent, ["intake_analyst", "scheduler"])
        self.assertIsNotNone(compiled)


class _FakeToolContext:
    def __init__(self, project_id: str):
        self.project_id = project_id

    async def graph_snapshot(self):
        return {"node_count": 0, "edge_count": 0, "warnings": [], "graph": {"nodes": [], "edges": []}}

    async def retrieve_context(self, query: str, limit: int = 5):
        return []

    async def recommended_integrations(self):
        return []

    async def record_decision(self, message: str):
        return None

    def storage_status(self):
        return {"graph": {"backend": "memory"}}

    def compliance_profile(self):
        return {"project_id": self.project_id, "category": "standard"}


if __name__ == "__main__":
    unittest.main()
