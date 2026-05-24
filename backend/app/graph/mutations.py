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

LINKABLE_LABELS = {
    NodeLabel.TASK,
    NodeLabel.MILESTONE,
    NodeLabel.DEPENDENCY,
    NodeLabel.RISK,
}

MANUAL_EDGE_TYPES = {
    EdgeType.RELATES_TO,
    EdgeType.DEPENDS_ON,
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
        self.adapter.upsert_node(project_id, node)
        self.adapter.upsert_edge(project_id, edge)
        return {
            "project_id": project_id,
            "node": node.model_dump(mode="json"),
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
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
        self.adapter.upsert_node(project_id, updated)
        return {
            "project_id": project_id,
            "node": updated.model_dump(mode="json"),
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
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
        self.adapter.delete_node(project_id, node_id)
        return {
            "project_id": project_id,
            "deleted_node_id": node_id,
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
        }

    def create_edge(
        self,
        project_id: str,
        *,
        source_id: str,
        target_id: str,
        edge_type: EdgeType = EdgeType.DEPENDS_ON,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if edge_type not in MANUAL_EDGE_TYPES:
            raise GraphMutationError(f"Edge type {edge_type.value} cannot be created manually")

        graph = self._require_graph(project_id)
        source = self._get_node(graph, source_id)
        target = self._get_node(graph, target_id)

        if source.label not in LINKABLE_LABELS or target.label not in LINKABLE_LABELS:
            raise GraphMutationError("Manual links require task, milestone, dependency, or risk nodes")

        if source_id == target_id:
            raise GraphMutationError("Cannot link a node to itself")

        edge = GraphEdge(
            source_id=source_id,
            target_id=target_id,
            type=edge_type,
            properties={"provenance": "manual_edit", **(properties or {})},
        )
        graph.edges = [
            item
            for item in graph.edges
            if not (
                item.source_id == source_id and item.target_id == target_id and item.type == edge_type
            )
        ]
        graph.edges.append(edge)
        self.adapter.upsert_edge(project_id, edge)
        return {
            "project_id": project_id,
            "edge": edge.model_dump(mode="json"),
            "edge_count": len(graph.edges),
        }

    def delete_edge(
        self,
        project_id: str,
        *,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
    ) -> dict[str, Any]:
        if edge_type not in MANUAL_EDGE_TYPES:
            raise GraphMutationError(f"Edge type {edge_type.value} cannot be deleted manually")

        graph = self._require_graph(project_id)
        before = len(graph.edges)
        graph.edges = [
            edge
            for edge in graph.edges
            if not (
                edge.source_id == source_id and edge.target_id == target_id and edge.type == edge_type
            )
        ]
        if len(graph.edges) == before:
            raise GraphMutationError("Edge not found")

        self.adapter.delete_edge(project_id, source_id, target_id, edge_type)
        return {
            "project_id": project_id,
            "deleted_edge": {
                "source_id": source_id,
                "target_id": target_id,
                "type": edge_type.value,
            },
            "edge_count": len(graph.edges),
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
