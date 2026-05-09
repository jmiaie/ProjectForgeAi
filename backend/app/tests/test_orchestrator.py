import tempfile
import unittest
from pathlib import Path

from agents.orchestrator import OrchestratorAgent
from agents.run_store import OrchestratorRunStore
from agents.state import OrchestratorRequest
from graph.builder import ProjectGraphBuilder
from ingestion.manifest import IngestionManifestStore
from ingestion.parsers.base import ParsedChunk, ParsedDocument


class OrchestratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_orchestrator_runs_specialist_steps(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_store = IngestionManifestStore(root=str(root / "manifests"))
            manifest_store.write(
                project_id="orch-test",
                documents=[
                    ParsedDocument(
                        source="kickoff.eml",
                        chunks=[
                            ParsedChunk(
                                source="kickoff.eml",
                                text="Kickoff approved",
                                metadata={
                                    "parser": "email",
                                    "source_hash": "hash",
                                    "chunk_index": 1,
                                    "chunk_size": 16,
                                },
                            )
                        ],
                        metadata={
                            "parser": "email",
                            "source": "kickoff.eml",
                            "source_hash": "hash",
                            "chunk_count": 1,
                        },
                        warnings=[],
                    )
                ],
                storage={"native_ready": False},
                session={"status": "started"},
            )
            graph_builder = ProjectGraphBuilder(manifest_store=manifest_store)
            graph_builder.build_from_latest_manifest("orch-test")

            agent = OrchestratorAgent(
                run_store=OrchestratorRunStore(root=str(root / "runs")),
                tool_context_factory=lambda project_id: _FakeToolContext(project_id, graph_builder),
            )
            result = await agent.run(
                OrchestratorRequest(
                    project_id="orch-test",
                    goal="Generate project operating plan",
                    run_id="run_fixed",
                )
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["run_id"], "run_fixed")
            self.assertEqual(len(result["steps"]), 5)
            self.assertIn("project_operating_plan", result["artifacts"])

            status = agent.status("orch-test", "run_fixed")
            self.assertEqual(status["status"], "completed")


class _FakeToolContext:
    def __init__(self, project_id: str, graph_builder: ProjectGraphBuilder):
        self.project_id = project_id
        self.graph_builder = graph_builder
        self.decisions: list[str] = []

    async def graph_snapshot(self):
        return self.graph_builder.get_graph(self.project_id)

    async def graph_status(self):
        return self.graph_builder.status(self.project_id)

    async def retrieve_context(self, query: str, limit: int = 5):
        return [{"source": "kickoff.eml", "text": "Kickoff approved"}]

    async def recommended_integrations(self):
        return ["google", "microsoft"]

    async def record_decision(self, message: str):
        self.decisions.append(message)

    def storage_status(self):
        return {"locus": {"native": False}, "ompa": {"native": False}, "graph": {"backend": "memory"}}


if __name__ == "__main__":
    unittest.main()
