import json
import tempfile
import unittest
from datetime import UTC, datetime
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from agents.orchestrator import OrchestratorAgent
from agents.run_store import OrchestratorRunStore
from agents.state import OrchestratorRequest
from core.config import settings
from graph.adapter import InMemoryGraphStore
from graph.builder import ProjectGraphBuilder
from graph.enricher import GraphEnrichmentService
from integrations.connectors.oauth import OAuthConnector, _pkce_challenge
from integrations.oauth_state_store import OAuthStateStore
from storage.locus_adapter import LocusAdapter


class Sprint345Tests(unittest.IsolatedAsyncioTestCase):
    def test_pkce_challenge_is_url_safe(self):
        challenge = _pkce_challenge("test-verifier-value")
        self.assertTrue(challenge)
        self.assertNotIn("=", challenge)

    def test_oauth_start_persists_pkce_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings.INTEGRATIONS_CONNECTION_ROOT = temp_dir
            connector = OAuthConnector("google", {"provider": "google", "scopes": ["email"]})
            payload = connector.start(project_id="proj", redirect_uri="http://localhost/callback")
            stored = OAuthStateStore().consume(payload["state"])
            assert stored is not None
            self.assertEqual(stored["connector_type"], "google")
            self.assertTrue(stored["code_verifier"])

    async def test_orchestrator_writes_step_checkpoints(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = OrchestratorRunStore(root=str(Path(temp_dir) / "runs"))
            agent = OrchestratorAgent(
                run_store=store,
                tool_context_factory=lambda project_id: _FakeToolContext(project_id),
            )
            result = await agent.run(
                OrchestratorRequest(project_id="chk", goal="Checkpoint test", run_id="run_chk")
            )
            self.assertEqual(result["status"], "completed")
            checkpoint_dir = Path(temp_dir) / "runs" / "chk" / "checkpoints" / "run_chk"
            self.assertTrue(any(checkpoint_dir.glob("step_*.json")))

    async def test_orchestrator_list_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = OrchestratorRunStore(root=str(Path(temp_dir) / "runs"))
            agent = OrchestratorAgent(
                run_store=store,
                tool_context_factory=lambda project_id: _FakeToolContext(project_id),
            )
            await agent.run(OrchestratorRequest(project_id="hist", goal="One"))
            listed = agent.list_runs("hist")
            self.assertEqual(len(listed["runs"]), 1)

    async def test_graph_rebuild_removes_orphans_in_memory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings.INGESTION_MANIFEST_ROOT = str(Path(temp_dir) / "ingestion")
            InMemoryGraphStore._graphs.clear()
            manifest_dir = Path(settings.INGESTION_MANIFEST_ROOT) / "orphan"
            manifest_dir.mkdir(parents=True, exist_ok=True)
            manifest = {
                "project_id": "orphan",
                "created_at": datetime.now(UTC).isoformat(),
                "files_processed": 1,
                "chunks_indexed": 1,
                "warnings": [],
                "documents": [
                    {
                        "source": "plan.pdf",
                        "metadata": {"parser": "pdf", "source_hash": "abc", "chunk_count": 1},
                        "warnings": [],
                        "chunks": [{"parser": "pdf", "source_hash": "abc", "chunk_index": 1}],
                    }
                ],
                "storage": {},
                "session": {},
            }
            (manifest_dir / "latest.json").write_text(json.dumps(manifest))
            builder = ProjectGraphBuilder()
            builder.build_from_latest_manifest("orphan")

            locus = LocusAdapter("orphan")
            await locus.index_files(
                [
                    {
                        "source": "plan.pdf",
                        "text": "Task: remove orphan nodes after rebuild",
                        "metadata": {"parser": "pdf", "source_hash": "abc", "chunk_index": 1, "source": "plan.pdf"},
                    }
                ]
            )
            enricher = GraphEnrichmentService(builder=builder)
            await enricher.enrich("orphan")
            before = builder.get_graph("orphan")
            self.assertGreater(before["node_count"], 3)

            rebuilt = builder.build_from_latest_manifest("orphan")
            after = builder.get_graph("orphan")
            self.assertLess(after["node_count"], before["node_count"])
            self.assertIn("orphans_removed", rebuilt["storage"])

    async def test_oauth_mock_token_exchange(self):
        connector = OAuthConnector("google", {"provider": "google", "scopes": ["email"]})
        with patch.object(settings, "OAUTH_MOCK_TOKEN_EXCHANGE", True), patch.object(
            settings, "OAUTH_ALLOW_UNVERIFIED_STATE", True
        ):
            token = await connector.authenticate({"code": "abc123", "state": None})
        self.assertTrue(token["access_token"].startswith("mock_access_"))


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
