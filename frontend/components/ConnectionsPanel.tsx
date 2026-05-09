'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { apiGet, apiPost, type ConnectionRecord } from '@/lib/api';
import IntakeWizard from '@/components/IntakeWizard';
import { StatusBadge } from '@/components/StatusBadge';

type ConnectionsPanelProps = {
  projectId: string;
  initialConnections: ConnectionRecord[];
};

export function ConnectionsPanel({ projectId, initialConnections }: ConnectionsPanelProps) {
  const [connections, setConnections] = useState(initialConnections);
  const [message, setMessage] = useState('');

  const refresh = async () => {
    const result = await apiGet<{ connections: ConnectionRecord[] }>(
      `/api/v1/intake/connections/${projectId}`,
    );
    setConnections(result.connections);
    setMessage(`Loaded ${result.connections.length} connection(s).`);
  };

  const startOAuth = async () => {
    const result = await apiPost<{ authorization_url: string }>(
      '/api/v1/intake/connections/oauth/start',
      { connector_type: 'google', project_id: projectId },
    );
    setMessage(`OAuth ready: ${result.authorization_url}`);
  };

  return (
    <Card className="panel">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Tooling</div>
          <h2>Connections</h2>
          <p className="muted">OAuth, API-key, and MCP connections with encrypted credentials.</p>
        </div>
        <div className="row">
          <Button variant="outline" onClick={refresh}>Refresh</Button>
          <Button onClick={startOAuth}>Start Google OAuth</Button>
        </div>
      </div>
      <div className="stack">
        {connections.length ? (
          connections.map((connection) => (
            <div className="stat" key={connection.connector_type}>
              <div className="row">
                <strong>{connection.connector_type.replace('_', ' ')}</strong>
                <StatusBadge status={connection.status} />
              </div>
            </div>
          ))
        ) : (
          <p className="muted">No connections yet.</p>
        )}
        {message ? <p className="muted">{message}</p> : null}
      </div>
      <div style={{ marginTop: '1rem' }}>
        <IntakeWizard projectId={projectId} onComplete={refresh} />
      </div>
    </Card>
  );
}
