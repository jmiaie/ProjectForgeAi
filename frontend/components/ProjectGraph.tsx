'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Edge,
  type Node,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { apiFetch, type ReactFlowPayload } from '@/lib/api';

type ProjectGraphProps = {
  projectId: string;
};

export default function ProjectGraph({ projectId }: ProjectGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<ReactFlowPayload>(
        `/api/v1/projects/${projectId}/graph/react-flow`,
      );
      setNodes(
        data.nodes.map((n) => ({
          id: n.id,
          position: n.position,
          data: { label: `${n.data.kind}: ${n.data.label}` },
        })),
      );
      setEdges(
        data.edges.map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.label,
        })),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load graph');
    } finally {
      setLoading(false);
    }
  }, [projectId, setNodes, setEdges]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return <p className="text-slate-600">Loading project graph…</p>;
  }

  if (error) {
    return (
      <div className="rounded border border-red-200 bg-red-50 p-4 text-red-800">
        <p>{error}</p>
        <button
          type="button"
          onClick={load}
          className="mt-2 text-sm underline"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="h-[70vh] w-full rounded-lg border border-slate-200 bg-white shadow-sm">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}
