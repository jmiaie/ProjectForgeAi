import tempfile
import unittest
from pathlib import Path

from agents.orchestrator import OrchestratorAgent
from agents.run_store import OrchestratorRunStore
from compliance.enforcer import ComplianceEnforcer
from core.config import settings
from fastapi.testclient import TestClient
from graph.models import GraphNode, NodeLabel, ProjectGraph
from projects.intelligence import PortfolioIntelligenceService
from projects.portfolio_orchestrator import PortfolioOrchestratorService, PortfolioRunStore
from projects.service import PortfolioService

import main


class Sprint17Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        settings.PROJECT_REGISTRY_ROOT = str(root / "projects")
        settings.COMPLIANCE_PROFILE_ROOT = str(root / "compliance")
        settings.COMPLIANCE_AUDIT_ROOT = str(root / "audit")
        settings.ORCHESTRATION_RUN_ROOT = str(root / "orchestrator")
        settings.DEFAULT_PROJECT_ID = "proj_123"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_compliance_rollup_groups_profiles(self):
        service = PortfolioService()
        service.create_project(name="Restricted", compliance="hipaa")
        service.create_project(name="Standard", compliance="standard")
        intelligence = PortfolioIntelligenceService()
        rollup = intelligence.compliance_rollup()
        self.assertGreaterEqual(rollup["totals"]["projects"], 2)
        self.assertGreaterEqual(rollup["totals"]["restricted_profiles"], 1)
        self.assertIn("hipaa", rollup["by_category"])

    def test_risk_rollup_counts_graph_risks(self):
        service = PortfolioService()
        created = service.create_project(name="Risky")
        intelligence = PortfolioIntelligenceService()
        graph = ProjectGraph(
            project_id=created.project_id,
            nodes=[
                GraphNode(
                    id=f"{created.project_id}:risk:1",
                    label=NodeLabel.RISK,
                    properties={"name": "Permit delay", "severity": "high"},
                ),
                GraphNode(
                    id=f"{created.project_id}:risk:2",
                    label=NodeLabel.RISK,
                    properties={"name": "Weather", "severity": "medium"},
                ),
            ],
        )
        intelligence.graph_builder.adapter.rebuild_graph(graph)
        rollup = intelligence.risk_rollup()
        self.assertGreaterEqual(rollup["totals"]["risks"], 2)
        self.assertEqual(rollup["by_severity"]["high"], 1)

    def test_executive_dashboard_widgets(self):
        intelligence = PortfolioIntelligenceService()
        dashboard = intelligence.executive_dashboard()
        self.assertIn("widgets", dashboard)
        self.assertIn("portfolio_health", dashboard["widgets"])
        self.assertIn("compliance_posture", dashboard["widgets"])
        self.assertIn("risk_summary", dashboard["widgets"])

    async def test_portfolio_orchestrator_run_across_projects(self):
        portfolio_service = PortfolioService()
        alpha = portfolio_service.create_project(name="Alpha")
        beta = portfolio_service.create_project(name="Beta")
        store = OrchestratorRunStore(root=str(Path(self.temp_dir.name) / "orch-runs"))
        agent = OrchestratorAgent(
            run_store=store,
            tool_context_factory=lambda project_id: _FakeToolContext(project_id),
        )
        portfolio_store = PortfolioRunStore(root=str(Path(self.temp_dir.name) / "orch-runs"))
        service = PortfolioOrchestratorService(
            orchestrator=agent,
            run_store=portfolio_store,
        )
        result = await service.run(
            goal="Portfolio risk sweep",
            project_ids=[alpha.project_id, beta.project_id],
        )
        self.assertEqual(len(result["project_runs"]), 2)
        self.assertEqual(result["status"], "completed")
        self.assertIn("compliance_findings", result["artifacts"])

    def test_portfolio_dashboard_api(self):
        client = TestClient(main.app)
        response = client.get("/api/v1/portfolio/intelligence/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn("widgets", response.json())

    def test_portfolio_compliance_rollup_api(self):
        client = TestClient(main.app)
        response = client.get("/api/v1/portfolio/compliance/rollup")
        self.assertEqual(response.status_code, 200)
        self.assertIn("by_category", response.json())

    async def test_portfolio_orchestrator_api(self):
        store = OrchestratorRunStore(root=str(Path(self.temp_dir.name) / "api-runs"))
        agent = OrchestratorAgent(
            run_store=store,
            tool_context_factory=lambda project_id: _FakeToolContext(project_id),
        )
        main.app.dependency_overrides[main.get_orchestrator_agent] = lambda: agent
        try:
            client = TestClient(main.app)
            response = client.post(
                "/api/v1/portfolio/orchestrator/run",
                json={"goal": "Executive portfolio review"},
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertIn("portfolio_run_id", payload)
            self.assertGreaterEqual(len(payload["project_runs"]), 1)
        finally:
            main.app.dependency_overrides.clear()


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
