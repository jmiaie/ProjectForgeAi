from datetime import UTC, datetime
from typing import Any

from compliance.audit import ComplianceAuditStore
from compliance.enforcer import ComplianceEnforcer
from graph.builder import ProjectGraphBuilder
from graph.models import NodeLabel
from projects.registry import ProjectRegistry

RESTRICTED_COMPLIANCE = {"hipaa", "legal", "gdpr"}


class PortfolioIntelligenceService:
    def __init__(
        self,
        registry: ProjectRegistry | None = None,
        graph_builder: ProjectGraphBuilder | None = None,
        compliance: ComplianceEnforcer | None = None,
        audit_store: ComplianceAuditStore | None = None,
    ):
        self.registry = registry or ProjectRegistry()
        self.graph_builder = graph_builder or ProjectGraphBuilder()
        self.compliance = compliance or ComplianceEnforcer()
        self.audit_store = audit_store or ComplianceAuditStore()

    def compliance_rollup(self, *, include_archived: bool = False) -> dict[str, Any]:
        projects = self.registry.list_projects(include_archived=include_archived)
        by_category: dict[str, int] = {}
        project_rows: list[dict[str, Any]] = []
        restricted_count = 0
        denied_total = 0
        audit_required_count = 0

        for project in projects:
            profile = self.compliance.get_profile(project.project_id)
            events = self.audit_store.list_events(project.project_id, limit=200)
            denied = [event for event in events if not event.get("allowed")]
            by_category[profile.category] = by_category.get(profile.category, 0) + 1
            if profile.category in RESTRICTED_COMPLIANCE:
                restricted_count += 1
            if profile.audit_required:
                audit_required_count += 1
            denied_total += len(denied)

            project_rows.append(
                {
                    "project_id": project.project_id,
                    "name": project.name,
                    "status": project.status,
                    "compliance": profile.category,
                    "restricted": profile.category in RESTRICTED_COMPLIANCE,
                    "audit_required": profile.audit_required,
                    "denied_actions": len(denied),
                    "recent_denials": denied[-3:],
                    "memory_writes_blocked": profile.allow_memory_writes is False,
                    "external_writes_gated": profile.require_human_approval_for_external_writes,
                }
            )

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "totals": {
                "projects": len(projects),
                "restricted_profiles": restricted_count,
                "audit_required": audit_required_count,
                "denied_actions": denied_total,
            },
            "by_category": by_category,
            "projects": project_rows,
        }

    def risk_rollup(self, *, include_archived: bool = False) -> dict[str, Any]:
        projects = self.registry.list_projects(include_archived=include_archived)
        by_severity: dict[str, int] = {"high": 0, "medium": 0, "low": 0, "unknown": 0}
        project_rows: list[dict[str, Any]] = []
        total_risks = 0

        for project in projects:
            graph_payload = self.graph_builder.get_graph(project.project_id)
            graph = graph_payload.get("graph", {})
            risk_nodes = [
                node
                for node in graph.get("nodes", [])
                if node.get("label") == NodeLabel.RISK.value
            ]
            project_severity = {"high": 0, "medium": 0, "low": 0, "unknown": 0}
            risks: list[dict[str, Any]] = []

            for node in risk_nodes:
                props = node.get("properties", {})
                severity = str(props.get("severity", "unknown")).lower()
                if severity not in project_severity:
                    severity = "unknown"
                project_severity[severity] += 1
                by_severity[severity] += 1
                risks.append(
                    {
                        "id": node.get("id"),
                        "name": props.get("name") or props.get("title") or node.get("id"),
                        "severity": severity,
                        "status": props.get("status", "open"),
                    }
                )

            total_risks += len(risk_nodes)
            project_rows.append(
                {
                    "project_id": project.project_id,
                    "name": project.name,
                    "status": project.status,
                    "risk_count": len(risk_nodes),
                    "by_severity": project_severity,
                    "top_risks": sorted(
                        risks,
                        key=lambda item: {"high": 0, "medium": 1, "low": 2, "unknown": 3}.get(
                            item["severity"], 4
                        ),
                    )[:5],
                }
            )

        project_rows.sort(key=lambda item: item["risk_count"], reverse=True)

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "totals": {
                "projects": len(projects),
                "risks": total_risks,
            },
            "by_severity": by_severity,
            "projects": project_rows,
        }

    def executive_dashboard(self, *, include_archived: bool = False) -> dict[str, Any]:
        projects = self.registry.list_projects(include_archived=include_archived)
        compliance = self.compliance_rollup(include_archived=include_archived)
        risks = self.risk_rollup(include_archived=include_archived)

        graphs_built = 0
        total_nodes = 0
        total_edges = 0
        for project in projects:
            status = self.graph_builder.status(project.project_id)
            if status["built"]:
                graphs_built += 1
            total_nodes += status["node_count"]
            total_edges += status["edge_count"]

        high_risk_projects = [
            row for row in risks["projects"] if row["by_severity"].get("high", 0) > 0
        ]
        compliance_gaps = [
            row
            for row in compliance["projects"]
            if row["restricted"] and row["denied_actions"] > 0
        ]

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "widgets": {
                "portfolio_health": {
                    "active_projects": len(projects),
                    "graphs_built": graphs_built,
                    "total_nodes": total_nodes,
                    "total_edges": total_edges,
                },
                "compliance_posture": {
                    "by_category": compliance["by_category"],
                    "restricted_profiles": compliance["totals"]["restricted_profiles"],
                    "denied_actions": compliance["totals"]["denied_actions"],
                    "projects_with_gaps": len(compliance_gaps),
                },
                "risk_summary": {
                    "total_risks": risks["totals"]["risks"],
                    "by_severity": risks["by_severity"],
                    "high_risk_projects": len(high_risk_projects),
                    "top_projects": risks["projects"][:5],
                },
            },
            "highlights": {
                "high_risk_projects": high_risk_projects[:5],
                "compliance_gaps": compliance_gaps[:5],
            },
        }
