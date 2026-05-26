'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { apiGet, type TenantBillingQuota } from '@/lib/api';

type TenantBillingPanelProps = {
  tenantId?: string;
};

export function TenantBillingPanel({ tenantId = 'tenant_default' }: TenantBillingPanelProps) {
  const [quota, setQuota] = useState<TenantBillingQuota | undefined>();

  const refresh = async () => {
    const result = await apiGet<TenantBillingQuota>(`/api/v1/tenants/${tenantId}/billing/quota`);
    setQuota(result);
  };

  useEffect(() => {
    refresh().catch(() => undefined);
  }, [tenantId]);

  if (!quota) {
    return (
      <Card className="panel">
        <p className="muted">Loading tenant billing…</p>
      </Card>
    );
  }

  return (
    <Card className="panel">
      <div className="panel-header">
        <div>
          <div className="eyebrow">SaaS billing</div>
          <h2>Tenant quotas</h2>
          <p className="muted">Usage and limits for {tenantId} ({quota.tier} tier).</p>
        </div>
        <Button variant="outline" onClick={refresh}>Refresh</Button>
      </div>
      <div className="grid grid-3">
        <div className="stat">
          <div className="stat-value">{quota.usage.projects}</div>
          <span className="muted">projects</span>
        </div>
        <div className="stat">
          <div className="stat-value">{quota.usage.api_requests}</div>
          <span className="muted">api requests</span>
        </div>
        <div className="stat">
          <div className="stat-value">{quota.usage.llm_tokens}</div>
          <span className="muted">llm tokens</span>
        </div>
      </div>
      <ul className="list">
        {Object.entries(quota.checks).map(([key, check]) => (
          <li key={key}>
            {key.replace('max_', '')}: {check.current}
            {check.limit != null ? ` / ${check.limit}` : ' · unlimited'}
            {check.allowed ? '' : ' · over quota'}
          </li>
        ))}
      </ul>
    </Card>
  );
}
