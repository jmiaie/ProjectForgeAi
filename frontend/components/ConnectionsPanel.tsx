'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { apiGet, apiPost, type ConnectionRecord } from '@/lib/api';
import IntakeWizard from '@/components/IntakeWizard';
import { StatusBadge } from '@/components/StatusBadge';

type ConnectionHealth = {
  connector: string;
  status: string;
  checks?: Record<string, unknown>;
};

type ConnectionsPanelProps = {
  projectId: string;
  initialConnections: ConnectionRecord[];
};

export function ConnectionsPanel({ projectId, initialConnections }: ConnectionsPanelProps) {
  const [connections, setConnections] = useState(initialConnections);
  const [health, setHealth] = useState<Record<string, ConnectionHealth>>({});
  const [mcpTools, setMcpTools] = useState<Array<Record<string, unknown>>>([]);
  const [message, setMessage] = useState('');

  const refresh = async () => {
    const result = await apiGet<{ connections: ConnectionRecord[] }>(
      `/api/v1/intake/connections/${projectId}`,
    );
    setConnections(result.connections);

    const healthEntries = await Promise.all(
      result.connections.map(async (connection) => {
        try {
          const payload = await apiGet<ConnectionHealth>(
            `/api/v1/intake/connections/${projectId}/${connection.connector_type}/health`,
          );
          return [connection.connector_type, payload] as const;
        } catch {
          return [
            connection.connector_type,
            { connector: connection.connector_type, status: 'unknown' },
          ] as const;
        }
      }),
    );
    setHealth(Object.fromEntries(healthEntries));
    setMessage(`Loaded ${result.connections.length} connection(s) with live health checks.`);
  };

  const startOAuth = async () => {
    const result = await apiPost<{ authorization_url: string }>(
      '/api/v1/intake/connections/oauth/start',
      { connector_type: 'google', project_id: projectId },
    );
    window.open(result.authorization_url, '_blank', 'noopener,noreferrer');
    setMessage('Opened Google OAuth authorization in a new tab.');
  };

  const loadMcpTools = async () => {
    const result = await apiGet<{ tools: Array<Record<string, unknown>> }>(
      `/api/v1/intake/connections/${projectId}/mcp/tools?connector_type=mcp_server`,
    );
    setMcpTools(result.tools ?? []);
    setMessage(`Discovered ${result.tools?.length ?? 0} MCP tool(s).`);
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
          <Button variant="outline" onClick={loadMcpTools}>MCP tools</Button>
          <Button onClick={startOAuth}>Start Google OAuth</Button>
        </div>
      </div>
      <div className="stack">
        {connections.length ? (
          connections.map((connection) => (
            <div className="stat" key={connection.connector_type}>
              <div className="row">
                <div>
                  <strong>{connection.connector_type.replace('_', ' ')}</strong>
                  <p className="muted">
                    {health[connection.connector_type]?.status ?? connection.status}
                    {health[connection.connector_type]?.checks?.tool_count !== undefined
                      ? ` · ${String(health[connection.connector_type]?.checks?.tool_count)} tools`
                      : ''}
                  </p>
                </div>
                <StatusBadge status={health[connection.connector_type]?.status ?? connection.status} />
              </div>
            </div>
          ))
        ) : (
          <p className="muted">No connections yet.</p>
        )}
        {mcpTools.length ? (
          <div className="stack">
            <div className="eyebrow">MCP tools</div>
            {mcpTools.map((tool, index) => (
              <div className="stat" key={`${String(tool.name ?? index)}`}>
                <strong>{String(tool.name ?? `tool-${index + 1}`)}</strong>
              </div>
            ))}
          </div>
        ) : null}
        {message ? <p className="muted">{message}</p> : null}
      </div>
      <div style={{ marginTop: '1rem' }}>
        <IntakeWizard projectId={projectId} onComplete={refresh} />
      </div>
    </Card>
  );
}
