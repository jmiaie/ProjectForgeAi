from typing import Any

from graph.adapter import Neo4jGraphAdapter
from graph.builder import ProjectGraphBuilder
from graph.ids import make_node_id
from graph.models import EdgeType, GraphEdge, GraphNode, NodeLabel, ProjectGraph

EDITABLE_LABELS = {
    NodeLabel.STAKEHOLDER,
    NodeLabel.TASK,
    NodeLabel.MILESTONE,
    NodeLabel.RISK,
    NodeLabel.DECISION,
    NodeLabel.DEPENDENCY,
}


class GraphMutationError(ValueError):
    pass


class GraphMutationService:
    def __init__(
        self,
        builder: ProjectGraphBuilder | None = None,
        adapter: Neo4jGraphAdapter | None = None,
    ):
        self.builder = builder or ProjectGraphBuilder()
        self.adapter = adapter or self.builder.adapter

    def create_node(
        self,
        project_id: str,
        *,
        label: NodeLabel,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        if label not in EDITABLE_LABELS:
            raise GraphMutationError(f"Label {label.value} cannot be created manually")

        graph = self._require_graph(project_id)
        name = str(properties.get("name") or properties.get("title") or "").strip()
        if not name:
            raise GraphMutationError("properties.name is required")

        node_id = make_node_id(project_id, label.value.lower(), name, "manual")
        if any(node.id == node_id for node in graph.nodes):
            raise GraphMutationError(f"Node {node_id} already exists")

        project_node = self._project_node(graph, project_id)
        node_properties = {
            "project_id": project_id,
            "name": name,
            "provenance": "manual_edit",
            **properties,
        }
        node = GraphNode(id=node_id, label=label, properties=node_properties)
        edge = GraphEdge(
            source_id=project_node.id,
            target_id=node_id,
            type=EdgeType.RELATES_TO,
            properties={"provenance": "manual_edit"},
        )
        graph.nodes.append(node)
        graph.edges.append(edge)
        self.adapter.upsert_graph(graph)
        return {
            "project_id": project_id,
            "node": node.model_dump(mode="json"),
            "node_count": graph.node_count,
            "edge_count": graph.edge_count,
        }

    def update_node(
        self,
        project_id: str,
        node_id: str,
        *,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        graph = self._require_graph(project_id)
        node = self._get_node(graph, node_id)
        if node.label not in EDITABLE_LABELS:
            raise GraphMutationError(f"Label {node.label.value} cannot be edited")

        merged = {**node.properties, **properties, "provenance": "manual_edit"}
        if "name" in properties and not str(properties["name"]).strip():
            raise GraphMutationError("properties.name cannot be empty")

        updated = GraphNode(id=node.id, label=node.label, properties=merged)
        graph.nodes = [updated if item.id == node_id else item for item in graph.nodes]
        self.adapter.upsert_graph(graph)
        return {
            "project_id": project_id,
            "node": updated.model_dump(mode="json"),
            "node_count": graph.node_count,
            "edge_count": graph.edge_count,
        }

    def delete_node(self, project_id: str, node_id: str) -> dict[str, Any]:
        graph = self._require_graph(project_id)
        node = self._get_node(graph, node_id)
        if node.label not in EDITABLE_LABELS:
            raise GraphMutationError(f"Label {node.label.value} cannot be deleted")

        graph.nodes = [item for item in graph.nodes if item.id != node_id]
        graph.edges = [
            edge
            for edge in graph.edges
            if edge.source_id != node_id and edge.target_id != node_id
        ]
        self.adapter.upsert_graph(graph)
        return {
            "project_id": project_id,
            "deleted_node_id": node_id,
            "node_count": graph.node_count,
            "edge_count": graph.edge_count,
        }

    def _require_graph(self, project_id: str) -> ProjectGraph:
        graph = self.adapter.get_graph(project_id)
        if graph is None:
            raise GraphMutationError(f"{project_id}: graph has not been built")
        return graph

    @staticmethod
    def _get_node(graph: ProjectGraph, node_id: str) -> GraphNode:
        for node in graph.nodes:
            if node.id == node_id:
                return node
        raise GraphMutationError(f"Node {node_id} not found")

    @staticmethod
    def _project_node(graph: ProjectGraph, project_id: str) -> GraphNode:
        for node in graph.nodes:
            if node.label == NodeLabel.PROJECT:
                return node
        raise GraphMutationError(f"{project_id}: project node missing from graph")
