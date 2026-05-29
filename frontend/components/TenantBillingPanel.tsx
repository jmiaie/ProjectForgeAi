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

type TenantOverage = {
  tenant_id: string;
  overage_tokens: number;
  overage_units_1k: number;
  estimated_cents: number;
};

type TenantBillingPanelProps = {
  tenantId?: string;
};

export function TenantBillingPanel({ tenantId = 'tenant_default' }: TenantBillingPanelProps) {
  const [quota, setQuota] = useState<TenantBillingQuota | undefined>();
  const [subscription, setSubscription] = useState<TenantSubscription['subscription']>();
  const [overage, setOverage] = useState<TenantOverage | undefined>();
  const [message, setMessage] = useState('');

  const refresh = async () => {
    const [quotaResult, subResult, overageResult] = await Promise.all([
      apiGet<TenantBillingQuota>(`/api/v1/tenants/${tenantId}/billing/quota`),
      apiGet<TenantSubscription>(`/api/v1/tenants/${tenantId}/billing/subscription`),
      apiGet<TenantOverage>(`/api/v1/tenants/${tenantId}/billing/overage`),
    ]);
    setQuota(quotaResult);
    setSubscription(subResult.subscription);
    setOverage(overageResult);
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

  const openCustomerPortal = async () => {
    setMessage('');
    try {
      const result = await apiPost<{ portal_url?: string; mode: string }>(
        `/api/v1/tenants/${tenantId}/billing/portal`,
        {},
      );
      setMessage(result.portal_url ? `Customer portal ready (${result.mode})` : 'Portal session created');
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Portal failed');
    }
  };

  const cancelSubscription = async () => {
    setMessage('');
    try {
      const result = await apiPost<{ status: string; at_period_end?: boolean }>(
        `/api/v1/tenants/${tenantId}/billing/subscription/cancel`,
        { at_period_end: false },
      );
      setMessage(`Subscription ${result.status}`);
      await refresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Cancel failed');
    }
  };

  const reportOverage = async () => {
    setMessage('');
    try {
      const result = await apiPost<{ status: string; mode?: string }>(
        `/api/v1/tenants/${tenantId}/billing/usage/report`,
        {},
      );
      setMessage(`Usage report ${result.status}${result.mode ? ` (${result.mode})` : ''}`);
      await refresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Usage report failed');
    }
  };

  const createOverageInvoice = async () => {
    setMessage('');
    try {
      const result = await apiPost<{ invoice?: { invoice_id: string } }>(
        `/api/v1/tenants/${tenantId}/billing/overage/invoice`,
        {},
      );
      setMessage(result.invoice ? `Overage invoice ${result.invoice.invoice_id} created` : 'Invoice created');
      await refresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Invoice failed');
    }
  };

  if (!quota) {
    return (
      <Card className="panel">
        <p className="muted">Loading tenant billing…</p>
      </Card>
    );
  }

  const hasActiveSubscription = subscription && subscription.status === 'active';

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
          {overage && overage.overage_tokens > 0 ? (
            <p className="muted">
              LLM overage: {overage.overage_tokens.toLocaleString()} tokens (~${(overage.estimated_cents / 100).toFixed(2)})
            </p>
          ) : null}
        </div>
        <Button variant="outline" onClick={refresh}>Refresh</Button>
        <Button variant="outline" onClick={startCheckout}>One-time checkout</Button>
        <Button onClick={startSubscription}>Subscribe (pro)</Button>
        {overage && overage.overage_tokens > 0 ? (
          <>
            <Button variant="outline" onClick={reportOverage}>Report overage</Button>
            <Button variant="outline" onClick={createOverageInvoice}>Create overage invoice</Button>
          </>
        ) : null}
        {hasActiveSubscription ? (
          <>
            <Button variant="outline" onClick={openCustomerPortal}>Customer portal</Button>
            <Button variant="outline" onClick={cancelSubscription}>Cancel subscription</Button>
          </>
        ) : null}
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
