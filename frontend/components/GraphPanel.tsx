'use client';

import { useState } from 'react';
import { GraphFlowViewer } from '@/components/GraphFlowViewer';
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

  const buildGraph = async () => {
    setMessage('Building graph from latest manifest...');
    const result = await apiPost<{ node_count: number; edge_count: number }>(
      `/api/v1/projects/${projectId}/graph/build`,
      {},
    );
    const nextStatus = await apiGet<GraphStatus>(`/api/v1/projects/${projectId}/graph/status`);
    setStatus(nextStatus);
    setRefreshKey((value) => value + 1);
    setMessage(`Graph built with ${result.node_count} nodes and ${result.edge_count} edges.`);
  };

  return (
    <div className="stack">
      <Card className="panel">
        <div className="panel-header">
          <div>
            <div className="eyebrow">Living Graph</div>
            <h2>Project graph</h2>
            <p className="muted">Manifest provenance becomes document and chunk graph nodes.</p>
          </div>
          <Button onClick={buildGraph}>Build graph</Button>
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
      <GraphFlowViewer projectId={projectId} refreshKey={refreshKey} />
    </div>
  );
}
