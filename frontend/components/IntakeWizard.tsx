'use client';

import { useEffect, useMemo, useState } from 'react';

type Connector = {
  name: string;
  type: string;
  provider?: string;
  description?: string;
  scopes?: string[];
  mcp_support?: boolean;
};

type IntakeWizardProps = {
  apiBaseUrl?: string;
  compliance?: string;
  projectId?: string;
  onComplete?: () => void;
};

const DEFAULT_API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export default function IntakeWizard({
  apiBaseUrl = DEFAULT_API_BASE,
  compliance = 'standard',
  projectId,
  onComplete,
}: IntakeWizardProps) {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [statusByConnector, setStatusByConnector] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadConnectors() {
      try {
        const res = await fetch(`${apiBaseUrl}/api/v1/intake/connectors?compliance=${compliance}`);
        if (!res.ok) throw new Error(`Failed to load connectors (${res.status})`);
        const data = await res.json();
        if (!cancelled) setConnectors(data.recommended ?? []);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadConnectors();
    return () => {
      cancelled = true;
    };
  }, [apiBaseUrl, compliance]);

  const sortedConnectors = useMemo(
    () => [...connectors].sort((a, b) => a.name.localeCompare(b.name)),
    [connectors],
  );

  async function handleConnect(connector: Connector) {
    setConnecting(connector.name);
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/intake/connections`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          connector_type: connector.name,
          auth_data: connector.type === 'mcp' ? { server_url: 'http://localhost:9000' } : {},
          project_id: projectId,
        }),
      });
      const payload = await res.json();
      setStatusByConnector((prev) => ({
        ...prev,
        [connector.name]: res.ok ? 'connected' : payload.detail ?? 'failed',
      }));
    } catch (err) {
      setStatusByConnector((prev) => ({
        ...prev,
        [connector.name]: err instanceof Error ? err.message : 'failed',
      }));
    } finally {
      setConnecting(null);
    }
  }

  return (
    <section className="mx-auto max-w-3xl rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
      <header className="mb-6">
        <h1 className="text-3xl font-bold text-slate-900">Connect Your Tools</h1>
        <p className="mt-2 text-sm text-slate-600">
          ProjectForge AI tailors the recommended integrations to your selected compliance tier
          (<span className="font-medium">{compliance}</span>). Connect any subset now &mdash; you can add more later.
        </p>
      </header>

      {loading && <p className="text-slate-500">Loading recommended connectors&hellip;</p>}
      {error && <p className="text-red-600">{error}</p>}

      {!loading && !error && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {sortedConnectors.map((connector) => {
            const status = statusByConnector[connector.name];
            return (
              <button
                key={connector.name}
                type="button"
                onClick={() => handleConnect(connector)}
                disabled={connecting === connector.name}
                className="flex h-24 flex-col items-start justify-center rounded-lg border border-slate-200 bg-slate-50 p-4 text-left transition hover:border-slate-400 hover:bg-white disabled:opacity-50"
              >
                <span className="text-lg font-semibold capitalize text-slate-900">
                  {connector.name.replace('_', ' ')}
                </span>
                <span className="text-xs uppercase tracking-wide text-slate-500">
                  {connector.type}
                  {connector.mcp_support ? ' · MCP' : ''}
                </span>
                {status && (
                  <span className="mt-1 text-xs font-medium text-emerald-700">{status}</span>
                )}
              </button>
            );
          })}
        </div>
      )}

      <footer className="mt-8 flex items-center justify-between">
        <span className="text-xs text-slate-500">
          {connectors.length} connector{connectors.length === 1 ? '' : 's'} available
        </span>
        <button
          type="button"
          onClick={onComplete}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
        >
          Skip &amp; Continue
        </button>
      </footer>
    </section>
  );
}
