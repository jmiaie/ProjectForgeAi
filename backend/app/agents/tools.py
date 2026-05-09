from typing import Any

from compliance.enforcer import ComplianceEnforcer
from core.integrations_manager import IntegrationsManager
from graph.builder import ProjectGraphBuilder
from storage.locus_adapter import LocusAdapter
from storage.ompa_adapter import OmpaAdapter


class OrchestratorToolContext:
    def __init__(
        self,
        project_id: str,
        graph_builder: ProjectGraphBuilder | None = None,
        integrations_manager: IntegrationsManager | None = None,
        compliance: ComplianceEnforcer | None = None,
    ):
        self.project_id = project_id
        self.graph_builder = graph_builder or ProjectGraphBuilder()
        self.integrations_manager = integrations_manager or IntegrationsManager()
        self.compliance = compliance or ComplianceEnforcer()
        self.locus = LocusAdapter(project_id)
        self.ompa = OmpaAdapter(project_id)

    async def graph_status(self) -> dict[str, Any]:
        return self.graph_builder.status(self.project_id)

    async def graph_snapshot(self) -> dict[str, Any]:
        graph = self.graph_builder.get_graph(self.project_id)
        if graph["node_count"] == 0:
            graph = self.graph_builder.build_from_latest_manifest(self.project_id)
        return graph

    async def retrieve_context(self, query: str, limit: int = 5) -> list[Any]:
        return await self.locus.retrieve(query, limit=limit)

    async def recommended_integrations(self) -> list[str]:
        return await self.integrations_manager.get_recommended_connectors(project_id=self.project_id)

    async def record_decision(self, message: str) -> None:
        await self.ompa.record_decision(message)

    def storage_status(self) -> dict[str, Any]:
        return {
            "locus": self.locus.status(),
            "ompa": self.ompa.status(),
            "graph": self.graph_builder.adapter.status(),
        }

    def compliance_profile(self) -> dict[str, Any]:
        return self.compliance.get_profile(self.project_id).as_dict()
