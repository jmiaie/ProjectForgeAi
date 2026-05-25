'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  apiGet,
  apiPost,
  type ExecutiveDashboard,
  type PortfolioOrchestratorRun,
} from '@/lib/api';

export function ExecutiveDashboardPanel() {
  const [dashboard, setDashboard] = useState<ExecutiveDashboard | undefined>();
  const [runs, setRuns] = useState<PortfolioOrchestratorRun[]>([]);
  const [message, setMessage] = useState('');

  const refresh = async () => {
    const [dash, runList] = await Promise.all([
      apiGet<ExecutiveDashboard>('/api/v1/portfolio/intelligence/dashboard'),
      apiGet<{ runs: PortfolioOrchestratorRun[] }>('/api/v1/portfolio/orchestrator/runs'),
    ]);
    setDashboard(dash);
    setRuns(runList.runs);
  };

  useEffect(() => {
    refresh().catch(() => undefined);
  }, []);

  const runPortfolioReview = async () => {
    setMessage('');
    try {
      const result = await apiPost<PortfolioOrchestratorRun>(
        '/api/v1/portfolio/orchestrator/run',
        { goal: 'Executive portfolio risk and compliance review' },
      );
      setMessage(
        `Portfolio run ${result.portfolio_run_id} completed across ${result.project_runs.length} project(s).`,
      );
      await refresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Portfolio orchestrator run failed');
    }
  };

  if (!dashboard) {
    return (
      <Card className="panel">
        <p className="muted">Loading executive dashboard…</p>
      </Card>
    );
  }

  const { portfolio_health, compliance_posture, risk_summary } = dashboard.widgets;

  return (
    <Card className="panel">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Executive</div>
          <h2>Portfolio intelligence</h2>
          <p className="muted">Cross-project compliance posture, risk rollups, and orchestrator activity.</p>
        </div>
        <div className="row">
          <Button variant="outline" onClick={refresh}>Refresh</Button>
          <Button onClick={runPortfolioReview}>Run portfolio review</Button>
        </div>
      </div>
      <div className="stack">
        <div className="grid grid-3">
          <div className="stat">
            <div className="stat-value">{portfolio_health.active_projects}</div>
            <span className="muted">active projects</span>
          </div>
          <div className="stat">
            <div className="stat-value">{compliance_posture.restricted_profiles}</div>
            <span className="muted">restricted profiles</span>
          </div>
          <div className="stat">
            <div className="stat-value">{risk_summary.total_risks}</div>
            <span className="muted">open risks</span>
          </div>
        </div>
        <div className="grid grid-2">
          <div className="stat">
            <strong>Compliance posture</strong>
            <p className="muted">
              {compliance_posture.denied_actions} denied action(s) ·{' '}
              {compliance_posture.projects_with_gaps} project(s) with gaps
            </p>
            <ul className="list">
              {Object.entries(compliance_posture.by_category).map(([category, count]) => (
                <li key={category}>
                  {category}: {count}
                </li>
              ))}
            </ul>
          </div>
          <div className="stat">
            <strong>Risk summary</strong>
            <p className="muted">
              {risk_summary.high_risk_projects} project(s) with high-severity risks
            </p>
            <ul className="list">
              {Object.entries(risk_summary.by_severity).map(([severity, count]) => (
                <li key={severity}>
                  {severity}: {count}
                </li>
              ))}
            </ul>
          </div>
        </div>
        {runs.length ? (
          <div className="stat">
            <strong>Recent portfolio runs</strong>
            <ul className="list">
              {runs.slice(0, 3).map((run) => (
                <li key={run.portfolio_run_id}>
                  {run.portfolio_run_id}: {run.project_runs.length} project(s) · {run.status}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {message ? <p className="muted">{message}</p> : null}
      </div>
    </Card>
  );
}
