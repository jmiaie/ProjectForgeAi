'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { apiDelete, apiGet, apiPost } from '@/lib/api';

type LLMKeyRecord = {
  provider: string;
  key_id: string;
  configured: boolean;
  updated_at: string;
};

type LLMUsageSummary = {
  call_count: number;
  total_tokens: number;
  flagship_calls: number;
  by_model: Record<string, number>;
};

type LLMRoutingPreview = {
  project_tier: string;
  economy_model: string;
  flagship_model: string;
  samples: Record<string, { model: string; routing_tier: string; reason: string; upsell_available: boolean }>;
};

type LLMPanelProps = {
  projectId: string;
};

export function LLMPanel({ projectId }: LLMPanelProps) {
  const [provider, setProvider] = useState('openai');
  const [apiKey, setApiKey] = useState('');
  const [keys, setKeys] = useState<LLMKeyRecord[]>([]);
  const [usage, setUsage] = useState<LLMUsageSummary | undefined>();
  const [routing, setRouting] = useState<LLMRoutingPreview | undefined>();
  const [message, setMessage] = useState('');

  const refresh = async () => {
    const [keysResult, usageResult, routingResult] = await Promise.all([
      apiGet<{ keys: LLMKeyRecord[] }>(`/api/v1/projects/${projectId}/llm/keys`),
      apiGet<LLMUsageSummary>(`/api/v1/projects/${projectId}/llm/usage`),
      apiGet<LLMRoutingPreview>(`/api/v1/projects/${projectId}/llm/routing`),
    ]);
    setKeys(keysResult.keys);
    setUsage(usageResult);
    setRouting(routingResult);
  };

  useEffect(() => {
    refresh().catch(() => undefined);
  }, [projectId]);

  const saveKey = async () => {
    if (!apiKey.trim()) {
      setMessage('Enter an API key.');
      return;
    }
    await apiPost(`/api/v1/projects/${projectId}/llm/keys`, { provider, api_key: apiKey });
    setApiKey('');
    setMessage(`Saved BYO key for ${provider}.`);
    await refresh();
  };

  const removeKey = async (keyProvider: string) => {
    await apiDelete(`/api/v1/projects/${projectId}/llm/keys/${keyProvider}`);
    setMessage(`Removed key for ${keyProvider}.`);
    await refresh();
  };

  return (
    <Card className="panel">
      <div className="panel-header">
        <div>
          <div className="eyebrow">LLM</div>
          <h2>Model routing & BYO keys</h2>
          <p className="muted">Flagship upsell routing, encrypted BYO provider keys, and per-project usage.</p>
        </div>
        <Button variant="outline" onClick={refresh}>Refresh</Button>
      </div>
      <div className="stack">
        {routing ? (
          <div className="stat">
            <strong>Tier: {routing.project_tier}</strong>
            <p className="muted">
              Economy: {routing.economy_model} · Flagship: {routing.flagship_model}
            </p>
            <p className="muted">
              Reasoning route: {routing.samples.reasoning.model} ({routing.samples.reasoning.routing_tier})
            </p>
            {routing.samples.reasoning.upsell_available ? (
              <p className="muted">Upgrade to pro for automatic flagship routing on reasoning tasks.</p>
            ) : null}
          </div>
        ) : null}
        {usage ? (
          <div className="grid grid-3">
            <div className="stat">
              <div className="stat-value">{usage.call_count}</div>
              <span className="muted">LLM calls</span>
            </div>
            <div className="stat">
              <div className="stat-value">{usage.total_tokens}</div>
              <span className="muted">tokens</span>
            </div>
            <div className="stat">
              <div className="stat-value">{usage.flagship_calls}</div>
              <span className="muted">flagship calls</span>
            </div>
          </div>
        ) : null}
        <div className="button-row">
          <select className="input" value={provider} onChange={(event) => setProvider(event.target.value)}>
            <option value="openai">openai</option>
            <option value="anthropic">anthropic</option>
            <option value="groq">groq</option>
            <option value="google">google</option>
          </select>
          <input
            className="input"
            type="password"
            placeholder="sk-..."
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
          />
          <Button onClick={saveKey}>Save BYO key</Button>
        </div>
        {keys.length ? (
          <div className="stack">
            {keys.map((key) => (
              <div className="stat row" key={key.key_id}>
                <div>
                  <strong>{key.provider}</strong>
                  <p className="muted">{key.key_id} · updated {key.updated_at}</p>
                </div>
                <Button variant="outline" onClick={() => removeKey(key.provider)}>Remove</Button>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No BYO keys configured for this project.</p>
        )}
        {message ? <p className="muted">{message}</p> : null}
      </div>
    </Card>
  );
}
