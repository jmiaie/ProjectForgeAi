'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { apiGet, apiPost, type OrchestratorAuditEvent, type OrchestratorRun } from '@/lib/api';
import { StatusBadge } from '@/components/StatusBadge';

type OrchestratorRunSummary = {
  run_id: string;
  status: string;
  goal: string;
  step_count: number;
  branch_path?: string;
  created_at?: string;
};

type OrchestratorPanelProps = {
  projectId: string;
};

export function OrchestratorPanel({ projectId }: OrchestratorPanelProps) {
  const [goal, setGoal] = useState('Create project operating plan');
  const [run, setRun] = useState<OrchestratorRun | undefined>();
  const [history, setHistory] = useState<OrchestratorRunSummary[]>([]);
  const [auditEvents, setAuditEvents] = useState<OrchestratorAuditEvent[]>([]);
  const [error, setError] = useState('');

  const loadHistory = async () => {
    const result = await apiGet<{ runs: OrchestratorRunSummary[] }>(
      `/api/v1/projects/${projectId}/orchestrator/runs?limit=5`,
    );
    setHistory(result.runs);
    if (!run && result.runs.length) {
      const latest = await apiGet<OrchestratorRun>(
        `/api/v1/projects/${projectId}/orchestrator/status?run_id=${result.runs[0].run_id}`,
      );
      if (latest.status !== 'missing') {
        setRun(latest);
      }
    }
  };

  const loadAudit = async (runId?: string) => {
    const query = runId ? `?run_id=${runId}&limit=20` : '?limit=20';
    const result = await apiGet<{ events: OrchestratorAuditEvent[] }>(
      `/api/v1/projects/${projectId}/orchestrator/audit${query}`,
    );
    setAuditEvents(result.events);
  };

  useEffect(() => {
    loadHistory().catch(() => undefined);
    loadAudit().catch(() => undefined);
  }, [projectId]);

  const runWorkflow = async () => {
    setError('');
    try {
      const result = await apiPost<OrchestratorRun>('/api/v1/orchestrator/run', {
        project_id: projectId,
        goal,
      });
      setRun(result);
      await loadHistory();
      await loadAudit(result.run_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to run orchestrator');
    }
  };

  const resumeWorkflow = async () => {
    if (!run?.run_id) return;
    setError('');
    try {
      const result = await apiPost<OrchestratorRun>('/api/v1/orchestrator/run', {
        project_id: projectId,
        goal: run.goal,
        run_id: run.run_id,
        resume: true,
      });
      setRun(result);
      await loadHistory();
      await loadAudit(result.run_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to resume orchestrator');
    }
  };

  return (
    <Card className="panel">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Agentic PM</div>
          <h2>Orchestrator</h2>
          <p className="muted">Run specialist steps against graph, Locus, OMPA, and integrations.</p>
        </div>
        {run ? <StatusBadge status={run.status} /> : null}
      </div>
      <div className="stack">
        <textarea
          className="input textarea"
          value={goal}
          onChange={(event) => setGoal(event.target.value)}
        />
        <div className="button-row">
          <Button onClick={runWorkflow}>Run orchestrator</Button>
          {run?.run_id ? (
            <Button variant="outline" onClick={resumeWorkflow}>Resume latest</Button>
          ) : null}
        </div>
        {error ? <p className="badge badge-warning">{error}</p> : null}
        {run ? (
          <div className="stack">
            {run.metadata?.branch_path ? (
              <p className="muted">Branch path: {String(run.metadata.branch_path)}</p>
            ) : null}
            {run.steps.map((step) => (
              <div className="stat" key={step.name}>
                <div className="row">
                  <strong>{step.name.replace('_', ' ')}</strong>
                  <StatusBadge status={step.status} />
                </div>
                <p className="muted">{step.summary}</p>
              </div>
            ))}
            {run.artifacts?.project_operating_plan ? (
              <pre className="code">
                {JSON.stringify(run.artifacts.project_operating_plan, null, 2)}
              </pre>
            ) : null}
          </div>
        ) : null}
        {auditEvents.length ? (
          <div className="stack">
            <div className="eyebrow">Orchestrator audit</div>
            {auditEvents.map((event) => (
              <div className="stat" key={event.id}>
                <strong>{event.event_type.replace('_', ' ')}</strong>
                <p className="muted">{event.message}</p>
              </div>
            ))}
          </div>
        ) : null}
        {history.length ? (
          <div className="stack">
            <div className="eyebrow">Recent runs</div>
            {history.map((entry) => (
              <div className="stat" key={entry.run_id}>
                <strong>{entry.run_id}</strong>
                <p className="muted">
                  {entry.status} · {entry.step_count} step(s)
                  {entry.branch_path ? ` · ${entry.branch_path}` : ''} · {entry.goal}
                </p>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </Card>
  );
}
