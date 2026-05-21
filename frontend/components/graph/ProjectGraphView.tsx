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

import { fetchReactFlow } from '@/lib/api';

type ProjectGraphViewProps = {
  projectId: string;
};

export default function ProjectGraphView({ projectId }: ProjectGraphViewProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await fetchReactFlow(projectId);
      setNodes(
        payload.nodes.map((node) => ({
          ...node,
          data: {
            ...node.data,
            label: (
              <div className="px-2 py-1">
                <div className="font-semibold text-slate-900">{node.data.label}</div>
                <div className="text-[10px] uppercase tracking-wide text-slate-500">
                  {node.data.kind}
                </div>
              </div>
            ),
          },
        })) as Node[],
      );
      setEdges(payload.edges as Edge[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load graph');
    } finally {
      setLoading(false);
    }
  }, [projectId, setEdges, setNodes]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <p className="text-slate-500">Loading graph…</p>;
  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <h3 className="font-semibold text-slate-900">Project graph</h3>
        <button
          type="button"
          onClick={load}
          className="rounded-md border border-slate-200 px-3 py-1 text-sm hover:bg-slate-50"
        >
          Refresh
        </button>
      </div>
      <div className="h-[560px] w-full">
        {nodes.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-slate-500">
            No graph nodes yet. Upload documents or run orchestration to populate the graph.
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            minZoom={0.2}
            maxZoom={1.5}
          >
            <MiniMap pannable zoomable />
            <Controls />
            <Background gap={16} size={1} />
          </ReactFlow>
        )}
      </div>
    </div>
  );
}
