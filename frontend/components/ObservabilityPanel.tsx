'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { apiGet, type ObservabilityMetrics } from '@/lib/api';

export function ObservabilityPanel() {
  const [metrics, setMetrics] = useState<ObservabilityMetrics | undefined>();

  const refresh = async () => {
    const result = await apiGet<ObservabilityMetrics>('/api/v1/observability/metrics');
    setMetrics(result);
  };

  useEffect(() => {
    refresh().catch(() => undefined);
  }, []);

  return (
    <Card className="panel">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Operations</div>
          <h2>Observability</h2>
          <p className="muted">Request metrics, error counts, and recent trace samples.</p>
        </div>
        <Button variant="outline" onClick={refresh}>Refresh</Button>
      </div>
      {metrics ? (
        <div className="stack">
          <p className="muted">
            Metrics {metrics.status.metrics_enabled ? 'enabled' : 'disabled'} · tracing{' '}
            {metrics.status.trace_requests ? 'on' : 'off'}
          </p>
          <div className="grid grid-3">
            <div className="stat">
              <div className="stat-value">{metrics.metrics.request_count ?? 0}</div>
              <span className="muted">requests</span>
            </div>
            <div className="stat">
              <div className="stat-value">{metrics.metrics.error_count ?? 0}</div>
              <span className="muted">errors</span>
            </div>
            <div className="stat">
              <div className="stat-value">{metrics.metrics.average_latency_ms ?? 0}</div>
              <span className="muted">avg ms</span>
            </div>
          </div>
          {metrics.recent_traces.length ? (
            <ul className="list">
              {metrics.recent_traces.slice(-5).map((trace) => (
                <li key={trace.trace_id}>
                  {trace.method} {trace.route} · {trace.status_code} · {trace.latency_ms}ms
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : (
        <p className="muted">Loading observability metrics…</p>
      )}
    </Card>
  );
}
