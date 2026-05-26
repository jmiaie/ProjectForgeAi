'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { apiGet, apiPost, type TenantBillingQuota } from '@/lib/api';

type TenantSubscription = {
  tenant_id: string;
  subscription: {
    subscription_id: string;
    status: string;
    target_tier?: string;
    billing_mode?: string;
  } | null;
};

type TenantBillingPanelProps = {
  tenantId?: string;
};

export function TenantBillingPanel({ tenantId = 'tenant_default' }: TenantBillingPanelProps) {
  const [quota, setQuota] = useState<TenantBillingQuota | undefined>();
  const [subscription, setSubscription] = useState<TenantSubscription['subscription']>();
  const [message, setMessage] = useState('');

  const refresh = async () => {
    const [quotaResult, subResult] = await Promise.all([
      apiGet<TenantBillingQuota>(`/api/v1/tenants/${tenantId}/billing/quota`),
      apiGet<TenantSubscription>(`/api/v1/tenants/${tenantId}/billing/subscription`),
    ]);
    setQuota(quotaResult);
    setSubscription(subResult.subscription);
  };

  useEffect(() => {
    refresh().catch(() => undefined);
  }, [tenantId]);

  const startCheckout = async () => {
    setMessage('');
    try {
      const result = await apiPost<{ checkout_url?: string; mode: string }>(
        `/api/v1/tenants/${tenantId}/billing/checkout`,
        { billing_mode: 'payment' },
      );
      setMessage(result.checkout_url ? `One-time checkout ready (${result.mode})` : 'Checkout created');
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Checkout failed');
    }
  };

  const startSubscription = async () => {
    setMessage('');
    try {
      const result = await apiPost<{ checkout_url?: string; mode: string; billing_mode: string }>(
        `/api/v1/tenants/${tenantId}/billing/subscribe`,
        { target_tier: 'pro' },
      );
      setMessage(
        result.checkout_url
          ? `Subscription checkout ready (${result.billing_mode})`
          : 'Subscription created',
      );
      await refresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Subscription failed');
    }
  };

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
          {subscription ? (
            <p className="muted">
              Subscription: {subscription.status}
              {subscription.target_tier ? ` · ${subscription.target_tier}` : ''}
            </p>
          ) : null}
        </div>
        <Button variant="outline" onClick={refresh}>Refresh</Button>
        <Button variant="outline" onClick={startCheckout}>One-time checkout</Button>
        <Button onClick={startSubscription}>Subscribe (pro)</Button>
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
      {message ? <p className="muted">{message}</p> : null}
    </Card>
  );
}
