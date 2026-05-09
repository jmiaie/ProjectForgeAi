"""Project graph schema.

Defines the canonical node and edge taxonomy used by the builder, adapters,
and the React Flow API. Keeping the taxonomy small and explicit makes it
easy to query both Neo4j and the in-memory fallback consistently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeKind(str, Enum):
    PROJECT = "Project"
    DOCUMENT = "Document"
    CHUNK = "Chunk"
    PERSON = "Person"
    ORGANIZATION = "Organization"
    MILESTONE = "Milestone"
    TASK = "Task"
    RISK = "Risk"
    CONTROL = "Control"
    CONTRACT = "Contract"
    COMMS_TEMPLATE = "CommsTemplate"
    CONNECTION = "Connection"


class EdgeKind(str, Enum):
    HAS_DOCUMENT = "HAS_DOCUMENT"
    CONTAINS_CHUNK = "CONTAINS_CHUNK"
    MENTIONS = "MENTIONS"
    ASSIGNED_TO = "ASSIGNED_TO"
    DEPENDS_ON = "DEPENDS_ON"
    MITIGATES = "MITIGATES"
    GOVERNS = "GOVERNS"
    GENERATED = "GENERATED"
    CONNECTED_VIA = "CONNECTED_VIA"


@dataclass(frozen=True)
class Node:
    id: str
    kind: NodeKind
    label: str
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "label": self.label,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Node":
        return cls(
            id=data["id"],
            kind=NodeKind(data["kind"]),
            label=data["label"],
            properties=data.get("properties", {}),
        )


@dataclass(frozen=True)
class Edge:
    id: str
    source: str
    target: str
    kind: EdgeKind
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "kind": self.kind.value,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Edge":
        return cls(
            id=data["id"],
            source=data["source"],
            target=data["target"],
            kind=EdgeKind(data["kind"]),
            properties=data.get("properties", {}),
        )
