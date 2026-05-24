from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class NodeLabel(StrEnum):
    PROJECT = "Project"
    DOCUMENT = "Document"
    CHUNK = "Chunk"
    STAKEHOLDER = "Stakeholder"
    TASK = "Task"
    MILESTONE = "Milestone"
    DECISION = "Decision"
    RISK = "Risk"
    DEPENDENCY = "Dependency"


class EdgeType(StrEnum):
    HAS_DOCUMENT = "HAS_DOCUMENT"
    HAS_CHUNK = "HAS_CHUNK"
    DERIVED_FROM = "DERIVED_FROM"
    RELATES_TO = "RELATES_TO"
    DEPENDS_ON = "DEPENDS_ON"


class GraphNode(BaseModel):
    id: str
    label: NodeLabel
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source_id: str
    target_id: str
    type: EdgeType
    properties: dict[str, Any] = Field(default_factory=dict)


class ProjectGraph(BaseModel):
    project_id: str
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)
