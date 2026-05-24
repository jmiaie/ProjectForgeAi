'use client';

import { useState } from 'react';
import { GraphFlowViewer } from '@/components/GraphFlowViewer';
import { TimelinePanel } from '@/components/TimelinePanel';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { apiGet, apiPost, type GraphStatus } from '@/lib/api';

type GraphPanelProps = {
  projectId: string;
  initialStatus?: GraphStatus;
};

export function GraphPanel({ projectId, initialStatus }: GraphPanelProps) {
  const [status, setStatus] = useState<GraphStatus | undefined>(initialStatus);
  const [message, setMessage] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);

  const refreshStatus = async () => {
    const nextStatus = await apiGet<GraphStatus>(`/api/v1/projects/${projectId}/graph/status`);
    setStatus(nextStatus);
    setRefreshKey((value) => value + 1);
    return nextStatus;
  };

  const buildGraph = async () => {
    setMessage('Building graph from latest manifest...');
    const result = await apiPost<{ node_count: number; edge_count: number }>(
      `/api/v1/projects/${projectId}/graph/build`,
      {},
    );
    await refreshStatus();
    setMessage(`Graph built with ${result.node_count} nodes and ${result.edge_count} edges.`);
  };

  const enrichGraph = async () => {
    setMessage('Enriching graph from indexed chunks...');
    const result = await apiPost<{ added_nodes: number; facts_extracted: number }>(
      `/api/v1/projects/${projectId}/graph/enrich`,
      { use_llm: false },
    );
    await refreshStatus();
    setMessage(
      `Graph enriched with ${result.added_nodes} new nodes from ${result.facts_extracted} extracted facts.`,
    );
  };

  const addTask = async () => {
    setMessage('Adding manual task node...');
    await apiPost(`/api/v1/projects/${projectId}/graph/nodes`, {
      label: 'Task',
      properties: {
        name: 'New project task',
        sequence: (status?.node_count ?? 0) + 1,
      },
    });
    await refreshStatus();
    setMessage('Manual task node added to the graph.');
  };

  return (
    <div className="stack">
      <Card className="panel">
        <div className="panel-header">
          <div>
            <div className="eyebrow">Living Graph</div>
            <h2>Project graph</h2>
            <p className="muted">Manifest provenance plus extracted stakeholder/task/risk/milestone facts.</p>
          </div>
          <div className="button-row">
            <Button variant="outline" onClick={buildGraph}>
              Build graph
            </Button>
            <Button variant="outline" onClick={enrichGraph}>Enrich graph</Button>
            <Button onClick={addTask}>Add task</Button>
          </div>
        </div>
        <div className="grid grid-2">
          <div className="stat">
            <div className="stat-value">{status?.node_count ?? 0}</div>
            <span className="muted">nodes</span>
          </div>
          <div className="stat">
            <div className="stat-value">{status?.edge_count ?? 0}</div>
            <span className="muted">edges</span>
          </div>
        </div>
        {message ? <p className="muted">{message}</p> : null}
      </Card>
      <GraphFlowViewer projectId={projectId} refreshKey={refreshKey} onGraphChanged={refreshStatus} />
      <TimelinePanel projectId={projectId} refreshKey={refreshKey} />
    </div>
  );
}
