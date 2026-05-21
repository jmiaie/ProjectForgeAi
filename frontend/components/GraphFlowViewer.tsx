'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Card } from '@/components/ui/card';
import { apiGet } from '@/lib/api';

type GraphNodeRecord = {
  id: string;
  label: string;
  properties: Record<string, unknown>;
};

type GraphEdgeRecord = {
  source_id: string;
  target_id: string;
  type: string;
};

type GraphResponse = {
  graph: {
    nodes: GraphNodeRecord[];
    edges: GraphEdgeRecord[];
  };
};

type GraphFlowViewerProps = {
  projectId: string;
  refreshKey?: number;
};

const labelColors: Record<string, string> = {
  Project: '#2563eb',
  Document: '#047857',
  Chunk: '#b45309',
  Stakeholder: '#7c3aed',
  Task: '#db2777',
  Milestone: '#0891b2',
  Risk: '#dc2626',
};

function layoutNodes(nodes: GraphNodeRecord[]): Node[] {
  const grouped: Record<string, GraphNodeRecord[]> = {};
  for (const node of nodes) {
    grouped[node.label] = grouped[node.label] || [];
    grouped[node.label].push(node);
  }

  const layers = ['Project', 'Document', 'Chunk', 'Stakeholder', 'Task', 'Milestone', 'Risk', 'Dependency'];
  const positioned: Node[] = [];

  layers.forEach((label, layerIndex) => {
    const layerNodes = grouped[label] || [];
    layerNodes.forEach((node, index) => {
      const title =
        (node.properties.source as string | undefined) ||
        (node.properties.project_id as string | undefined) ||
        node.label;
      positioned.push({
        id: node.id,
        position: {
          x: index * 240,
          y: layerIndex * 140,
        },
        data: {
          label: `${node.label}: ${title}`,
        },
        style: {
          border: `2px solid ${labelColors[node.label] || '#64748b'}`,
          borderRadius: 12,
          padding: 10,
          fontSize: 12,
          width: 210,
          background: '#ffffff',
        },
      });
    });
  });

  return positioned;
}

function layoutEdges(edges: GraphEdgeRecord[]): Edge[] {
  return edges.map((edge, index) => ({
    id: `${edge.source_id}-${edge.target_id}-${index}`,
    source: edge.source_id,
    target: edge.target_id,
    label: edge.type.replaceAll('_', ' '),
    animated: true,
  }));
}

export function GraphFlowViewer({ projectId, refreshKey = 0 }: GraphFlowViewerProps) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [message, setMessage] = useState('Loading graph...');

  useEffect(() => {
    let active = true;
    setMessage('Loading graph...');
    apiGet<GraphResponse>(`/api/v1/projects/${projectId}/graph`)
      .then((response) => {
        if (!active) return;
        const graphNodes = response.graph?.nodes ?? [];
        if (!graphNodes.length) {
          setNodes([]);
          setEdges([]);
          setMessage('No graph nodes yet. Upload documents and build the graph.');
          return;
        }
        setNodes(layoutNodes(graphNodes));
        setEdges(layoutEdges(response.graph?.edges ?? []));
        setMessage(`${graphNodes.length} nodes visualized`);
      })
      .catch(() => {
        if (!active) return;
        setNodes([]);
        setEdges([]);
        setMessage('Graph viewer unavailable until backend is reachable.');
      });
    return () => {
      active = false;
    };
  }, [projectId, refreshKey]);

  const proOptions = useMemo(() => ({ hideAttribution: true }), []);

  return (
    <Card className="panel">
      <div className="panel-header">
        <div>
          <div className="eyebrow">React Flow</div>
          <h2>Graph viewer</h2>
          <p className="muted">{message}</p>
        </div>
      </div>
      <div className="flow-shell">
        <ReactFlow nodes={nodes} edges={edges} fitView proOptions={proOptions}>
          <MiniMap />
          <Controls />
          <Background gap={16} size={1} />
        </ReactFlow>
      </div>
    </Card>
  );
}
