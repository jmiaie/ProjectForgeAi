'use client';

import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

export default function IntakeWizard({ onComplete }: { onComplete: () => void }) {
  const [step] = useState(0);
  const [recommended, setRecommended] = useState<string[]>([
    'google',
    'microsoft',
    'slack',
    'github',
    'jira',
    'mcp_server',
  ]);
  const [status, setStatus] = useState<string>('');
  const projectId = 'proj_123';

  useEffect(() => {
    const loadRecommended = async () => {
      try {
        const response = await fetch(`/api/v1/intake/recommended?project_id=${projectId}`);
        if (!response.ok) {
          return;
        }
        const payload = await response.json();
        const names = (payload.connectors ?? []).map((connector: { name: string }) => connector.name);
        if (names.length > 0) {
          setRecommended(names);
        }
      } catch {
        // keep local defaults when backend is unavailable.
      }
    };
    void loadRecommended();
  }, []);

  const handleConnect = async (type: string) => {
    try {
      setStatus(`Connecting ${type} (step ${step})...`);
      if (type === 'jira') {
        const response = await fetch('/api/v1/intake/api-key', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            connector_type: 'jira',
            project_id: projectId,
            api_key: 'replace-me-jira-api-key',
          }),
        });
        const payload = await response.json();
        setStatus(
          response.ok
            ? `${type} connected (${payload.connection?.auth?.token_masked ?? 'masked token'})`
            : `Failed to connect ${type}: ${payload.detail ?? 'unknown error'}`
        );
        return;
      }

      if (type === 'mcp_server') {
        const response = await fetch('/api/v1/intake/mcp', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            connector_type: 'mcp_server',
            project_id: projectId,
            server_url: 'https://example-mcp-server.local',
          }),
        });
        const payload = await response.json();
        setStatus(
          response.ok
            ? `${type} status: ${payload.status} (${payload.connection?.auth?.mode ?? 'unknown'})`
            : `Failed to connect ${type}: ${payload.detail ?? 'unknown error'}`
        );
        return;
      }

      const oauthStart = await fetch('/api/v1/intake/oauth/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          connector_type: type,
          project_id: projectId,
          redirect_uri: 'http://localhost:3000/settings/connections/callback',
        }),
      });
      const startPayload = await oauthStart.json();
      if (!oauthStart.ok) {
        setStatus(`Failed to start ${type} OAuth: ${startPayload.detail ?? 'unknown error'}`);
        return;
      }
      setStatus(`OAuth started for ${type}. Open: ${startPayload.authorization_url}`);
    } catch (error) {
      setStatus(`Failed to connect ${type}: ${String(error)}`);
    }
  };

  return (
    <Card className="mx-auto max-w-2xl p-8">
      <h1 className="mb-8 text-3xl font-bold">Connect Your Tools</h1>
      <div className="grid grid-cols-2 gap-4">
        {recommended.map((tool) => (
          <Button
            key={tool}
            variant="outline"
            className="h-24 flex-col"
            onClick={() => handleConnect(tool)}
          >
            <span className="text-lg capitalize">{tool}</span>
          </Button>
        ))}
      </div>
      {status ? <p className="mt-6 text-sm text-slate-600">{status}</p> : null}
      <Button onClick={onComplete} className="mt-8 w-full">
        Skip &amp; Continue
      </Button>
    </Card>
  );
}
