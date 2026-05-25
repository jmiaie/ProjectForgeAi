'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { apiGet, apiPost, type UpgradeStatus } from '@/lib/api';

type AccessPanelProps = {
  projectId: string;
};

export function AccessPanel({ projectId }: AccessPanelProps) {
  const [upgrade, setUpgrade] = useState<UpgradeStatus | undefined>();
  const [message, setMessage] = useState('');

  useEffect(() => {
    apiGet<UpgradeStatus>(`/api/v1/projects/${projectId}/upgrade/status`)
      .then(setUpgrade)
      .catch(() => setUpgrade(undefined));
  }, [projectId]);

  const runSelfImprove = async () => {
    setMessage('');
    try {
      await apiPost(`/api/v1/projects/${projectId}/upgrade/self-improve`, {
        goal: 'Review project graph and propose operating improvements',
      });
      setMessage('Self-improvement orchestrator run completed.');
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Self-improvement blocked');
    }
  };

  return (
    <Card className="panel">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Enterprise</div>
          <h2>Access & upgrades</h2>
          <p className="muted">Feature tiers and compliance-gated self-improvement.</p>
        </div>
      </div>
      {upgrade ? (
        <div className="stack">
          <p className="muted">
            Tier: {upgrade.project_tier} · Deployment: {upgrade.deployment_mode} · Compliance:{' '}
            {upgrade.compliance_category}
          </p>
          <div className="stack">
            {Object.entries(upgrade.features).map(([feature, meta]) => (
              <div className="stat" key={feature}>
                <strong>{feature.replace(/_/g, ' ')}</strong>
                <p className="muted">
                  {meta.enabled ? 'enabled' : 'locked'} · requires {meta.required_tier}
                </p>
              </div>
            ))}
          </div>
          <Button
            variant="outline"
            disabled={!upgrade.features.self_learning?.enabled}
            onClick={runSelfImprove}
          >
            Run self-improvement
          </Button>
        </div>
      ) : (
        <p className="muted">Upgrade status unavailable.</p>
      )}
      {message ? <p className="muted">{message}</p> : null}
    </Card>
  );
}
