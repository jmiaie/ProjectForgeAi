"""Project graph query routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.graph.adapter import get_graph_adapter
from app.graph.schema import EdgeKind, NodeKind

router = APIRouter(prefix="/projects/{project_id}/graph", tags=["graph"])


@router.get("/")
async def get_graph(project_id: str) -> dict[str, Any]:
    snapshot = await get_graph_adapter().get_snapshot(project_id)
    return {
        "project_id": project_id,
        "nodes": [n.to_dict() for n in snapshot.nodes],
        "edges": [e.to_dict() for e in snapshot.edges],
    }


@router.get("/stats")
async def get_graph_stats(project_id: str) -> dict[str, Any]:
    snapshot = await get_graph_adapter().get_snapshot(project_id)
    return snapshot.stats()


@router.get("/react-flow")
async def get_react_flow_payload(project_id: str) -> dict[str, Any]:
    snapshot = await get_graph_adapter().get_snapshot(project_id)
    return snapshot.to_react_flow()


@router.get("/nodes/{node_id}")
async def get_graph_node(project_id: str, node_id: str) -> dict[str, Any]:
    node = await get_graph_adapter().get_node(project_id, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return node.to_dict()


@router.get("/schema")
async def get_graph_schema() -> dict[str, Any]:
    return {
        "node_kinds": [kind.value for kind in NodeKind],
        "edge_kinds": [kind.value for kind in EdgeKind],
    }
