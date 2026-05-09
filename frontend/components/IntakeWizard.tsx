'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

type IntakeWizardProps = {
  onComplete?: () => void;
};

export default function IntakeWizard({ onComplete }: IntakeWizardProps) {
  const [recommended, setRecommended] = useState<string[]>([
    'google',
    'microsoft',
    'slack',
    'github',
    'mcp_server',
  ]);
  const [status, setStatus] = useState<string>('');

  useEffect(() => {
    fetch('/api/v1/intake/connections/recommended')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.connectors) setRecommended(data.connectors);
      })
      .catch(() => {
        // Local UI preview can run before the backend proxy is configured.
      });
  }, []);

  const handleConnect = async (type: string) => {
    setStatus(`Connecting to ${type}...`);
    const payload =
      type === 'mcp_server'
        ? { server_url: 'https://example-mcp.local' }
        : { code: 'placeholder-oauth-code' };

    const response = await fetch('/api/v1/intake/connections', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ connector_type: type, auth_data: payload }),
    });

    setStatus(response.ok ? `${type} connected` : `${type} needs configuration`);
  };

  return (
    <Card className="mx-auto max-w-2xl p-8">
      <h1 className="mb-2 text-3xl font-bold">Connect Your Tools</h1>
      <p className="mb-8 text-sm text-muted-foreground">
        ProjectForge can ingest calendars, files, chat, issue trackers, and MCP tools.
      </p>
      <div className="grid grid-cols-2 gap-4">
        {recommended.map((tool) => (
          <Button
            key={tool}
            variant="outline"
            className="h-24 flex-col"
            onClick={() => handleConnect(tool)}
          >
            <span className="text-lg capitalize">{tool.replace('_', ' ')}</span>
          </Button>
        ))}
      </div>
      {status ? <p className="mt-4 text-sm">{status}</p> : null}
      <Button onClick={onComplete} className="mt-8 w-full">
        Skip & Continue
      </Button>
    </Card>
  );
}
