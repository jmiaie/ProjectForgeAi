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
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { apiDelete, apiGet, apiPatch } from '@/lib/api';

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
  onGraphChanged?: () => void;
};

const EDITABLE_LABELS = new Set(['Stakeholder', 'Task', 'Milestone', 'Risk', 'Decision', 'Dependency']);

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
        (node.properties.name as string | undefined) ||
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

export function GraphFlowViewer({ projectId, refreshKey = 0, onGraphChanged }: GraphFlowViewerProps) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [rawNodes, setRawNodes] = useState<GraphNodeRecord[]>([]);
  const [selectedNode, setSelectedNode] = useState<GraphNodeRecord | null>(null);
  const [editName, setEditName] = useState('');
  const [editSequence, setEditSequence] = useState('');
  const [editSeverity, setEditSeverity] = useState('');
  const [message, setMessage] = useState('Loading graph...');
  const [saving, setSaving] = useState(false);

  const loadGraph = () => {
    setMessage('Loading graph...');
    return apiGet<GraphResponse>(`/api/v1/projects/${projectId}/graph`)
      .then((response) => {
        const graphNodes = response.graph?.nodes ?? [];
        setRawNodes(graphNodes);
        if (!graphNodes.length) {
          setNodes([]);
          setEdges([]);
          setSelectedNode(null);
          setMessage('No graph nodes yet. Upload documents and build the graph.');
          return;
        }
        setNodes(layoutNodes(graphNodes));
        setEdges(layoutEdges(response.graph?.edges ?? []));
        setMessage(`${graphNodes.length} nodes visualized`);
      })
      .catch(() => {
        setNodes([]);
        setEdges([]);
        setRawNodes([]);
        setSelectedNode(null);
        setMessage('Graph viewer unavailable until backend is reachable.');
      });
  };

  useEffect(() => {
    let active = true;
    loadGraph().then(() => {
      if (!active) return;
    });
    return () => {
      active = false;
    };
  }, [projectId, refreshKey]);

  useEffect(() => {
    if (!selectedNode) {
      setEditName('');
      setEditSequence('');
      setEditSeverity('');
      return;
    }
    setEditName(String(selectedNode.properties.name ?? ''));
    setEditSequence(String(selectedNode.properties.sequence ?? ''));
    setEditSeverity(String(selectedNode.properties.severity ?? ''));
  }, [selectedNode]);

  const proOptions = useMemo(() => ({ hideAttribution: true }), []);
  const editable = selectedNode ? EDITABLE_LABELS.has(selectedNode.label) : false;

  const saveNode = async () => {
    if (!selectedNode) return;
    setSaving(true);
    try {
      const properties: Record<string, unknown> = {
        name: editName.trim(),
      };
      if (editSequence.trim()) {
        properties.sequence = Number(editSequence);
      }
      if (editSeverity.trim()) {
        properties.severity = editSeverity.trim();
      }
      await apiPatch(`/api/v1/projects/${projectId}/graph/nodes/${selectedNode.id}`, { properties });
      setMessage(`Updated ${selectedNode.label} node.`);
      onGraphChanged?.();
      await loadGraph();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to update node.');
    } finally {
      setSaving(false);
    }
  };

  const deleteNode = async () => {
    if (!selectedNode) return;
    setSaving(true);
    try {
      await apiDelete(`/api/v1/projects/${projectId}/graph/nodes/${selectedNode.id}`);
      setSelectedNode(null);
      setMessage(`Deleted ${selectedNode.label} node.`);
      onGraphChanged?.();
      await loadGraph();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to delete node.');
    } finally {
      setSaving(false);
    }
  };

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
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          proOptions={proOptions}
          onNodeClick={(_, node) => {
            const match = rawNodes.find((item) => item.id === node.id) ?? null;
            setSelectedNode(match);
          }}
        >
          <MiniMap />
          <Controls />
          <Background gap={16} size={1} />
        </ReactFlow>
      </div>
      {selectedNode ? (
        <div className="drawer">
          <div className="drawer-header">
            <strong>{selectedNode.label}</strong>
            <button className="link-button" type="button" onClick={() => setSelectedNode(null)}>
              Close
            </button>
          </div>
          {editable ? (
            <div className="stack">
              <label className="field">
                <span>Name</span>
                <input value={editName} onChange={(event) => setEditName(event.target.value)} />
              </label>
              {(selectedNode.label === 'Task' || selectedNode.label === 'Milestone') ? (
                <label className="field">
                  <span>Sequence</span>
                  <input value={editSequence} onChange={(event) => setEditSequence(event.target.value)} />
                </label>
              ) : null}
              {selectedNode.label === 'Risk' ? (
                <label className="field">
                  <span>Severity</span>
                  <input value={editSeverity} onChange={(event) => setEditSeverity(event.target.value)} />
                </label>
              ) : null}
              <div className="button-row">
                <Button disabled={saving || !editName.trim()} onClick={saveNode}>Save</Button>
                <Button variant="outline" disabled={saving} onClick={deleteNode}>Delete</Button>
              </div>
            </div>
          ) : (
            <pre className="code">{JSON.stringify(selectedNode.properties, null, 2)}</pre>
          )}
        </div>
      ) : null}
    </Card>
  );
}
