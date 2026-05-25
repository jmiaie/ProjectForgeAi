from typing import Any

from compliance.enforcer import ComplianceEnforcer
from graph.builder import ProjectGraphBuilder
from projects.registry import ProjectRegistry, ProjectRecord


class PortfolioService:
    def __init__(
        self,
        registry: ProjectRegistry | None = None,
        graph_builder: ProjectGraphBuilder | None = None,
        compliance: ComplianceEnforcer | None = None,
    ):
        self.registry = registry or ProjectRegistry()
        self.graph_builder = graph_builder or ProjectGraphBuilder()
        self.compliance = compliance or ComplianceEnforcer()

    def list_projects(self, *, include_archived: bool = False) -> dict[str, Any]:
        projects = self.registry.list_projects(include_archived=include_archived)
        return {
            "count": len(projects),
            "projects": [project.as_dict() for project in projects],
        }

    def get_project(self, project_id: str) -> dict[str, Any]:
        record = self.registry.get(project_id)
        if record is None:
            raise ValueError(f"Unknown project: {project_id}")
        return record.as_dict()

    def create_project(
        self,
        *,
        name: str,
        compliance: str = "standard",
        tier: str | None = None,
    ) -> ProjectRecord:
        record = self.registry.create(name=name, compliance=compliance, tier=tier)
        self.compliance.set_profile(record.project_id, record.compliance)
        return record

    def archive_project(self, project_id: str) -> ProjectRecord:
        return self.registry.archive(project_id)

    def portfolio_summary(self, *, include_archived: bool = False) -> dict[str, Any]:
        projects = self.registry.list_projects(include_archived=include_archived)
        summaries = []
        totals = {"projects": 0, "nodes": 0, "edges": 0, "archived": 0}

        for project in projects:
            graph = self.graph_builder.status(project.project_id)
            profile = self.compliance.get_profile(project.project_id)
            summaries.append(
                {
                    "project_id": project.project_id,
                    "name": project.name,
                    "status": project.status,
                    "tier": project.tier,
                    "compliance": profile.category,
                    "graph_built": graph["built"],
                    "node_count": graph["node_count"],
                    "edge_count": graph["edge_count"],
                    "updated_at": project.updated_at,
                }
            )
            totals["projects"] += 1
            totals["nodes"] += graph["node_count"]
            totals["edges"] += graph["edge_count"]
            if project.status == "archived":
                totals["archived"] += 1

        return {
            "totals": totals,
            "projects": summaries,
        }
