'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { StatusBadge } from '@/components/StatusBadge';
import { apiGet, apiPost, type AutomationRecord } from '@/lib/api';

type AutomationRun = {
  automation_id: string;
  status: string;
  attempt?: number;
  error?: string;
  created_at?: string;
};

type TemporalStatus = {
  address: string;
  task_queue: string;
  use_worker_dispatch: boolean;
  temporal_sync_schedules?: boolean;
};

type AutomationsPanelProps = {
  projectId: string;
  initialAutomations: AutomationRecord[];
};

export function AutomationsPanel({ projectId, initialAutomations }: AutomationsPanelProps) {
  const [automations, setAutomations] = useState(initialAutomations);
  const [deadLetters, setDeadLetters] = useState<AutomationRun[]>([]);
  const [runs, setRuns] = useState<AutomationRun[]>([]);
  const [temporal, setTemporal] = useState<TemporalStatus | null>(null);
  const [message, setMessage] = useState('');

  const refresh = async () => {
    const [items, deadLetterItems, runItems, temporalStatus] = await Promise.all([
      apiGet<{ automations: AutomationRecord[] }>(`/api/v1/projects/${projectId}/automations`),
      apiGet<{ dead_letters: AutomationRun[] }>(`/api/v1/projects/${projectId}/automations/dead-letters`),
      apiGet<{ runs: AutomationRun[] }>(`/api/v1/projects/${projectId}/automations/runs?limit=10`),
      apiGet<TemporalStatus>('/api/v1/automations/temporal/status'),
    ]);
    setAutomations(items.automations);
    setDeadLetters(deadLetterItems.dead_letters);
    setRuns(runItems.runs);
    setTemporal(temporalStatus);
  };

  const createReminder = async () => {
    const result = await apiPost<AutomationRecord>(`/api/v1/projects/${projectId}/automations`, {
      type: 'timed_reminder',
      name: 'Review project plan',
      payload: { message: 'Review the latest ProjectForge operating plan', recipient: 'project_owner' },
      schedule: { interval_seconds: 3600 },
    });
    setMessage(`Created ${result.name} (next run ${result.next_run_at ?? 'unscheduled'}).`);
    await refresh();
  };

  const createApprovalGate = async () => {
    const result = await apiPost<AutomationRecord>(`/api/v1/projects/${projectId}/automations`, {
      type: 'approval_gate',
      name: 'Release weekly report',
      payload: { message: 'Approve weekly report release' },
      requires_approval: true,
    });
    setMessage(`Created approval gate ${result.name}.`);
    await refresh();
  };

  const approveAutomation = async (automationId: string) => {
    await apiPost(`/api/v1/projects/${projectId}/automations/${automationId}/approve`, {
      approved_by: 'project_owner',
    });
    setMessage('Automation approved.');
    await refresh();
  };

  const runAutomation = async (automationId: string) => {
    const result = await apiPost<{ status: string; retriable?: boolean }>(
      `/api/v1/projects/${projectId}/automations/${automationId}/run`,
      {},
    );
    setMessage(
      result.retriable
        ? `Run failed but is scheduled for retry (${result.status}).`
        : `Run finished with ${result.status}.`,
    );
    await refresh();
  };

  const retryAutomation = async (automationId: string) => {
    const result = await apiPost<{ status: string }>(
      `/api/v1/projects/${projectId}/automations/${automationId}/retry`,
      {},
    );
    setMessage(`Retry finished with ${result.status}.`);
    await refresh();
  };

  const runDue = async () => {
    const result = await apiPost<{ processed: number; dispatch?: string }>(
      '/api/v1/automations/temporal/run-due',
      {},
    );
    setMessage(`Temporal runner processed ${result.processed} due automation(s) via ${result.dispatch ?? 'local'}.`);
    await refresh();
  };

  return (
    <Card className="panel">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Durable Workflows</div>
          <h2>Automations</h2>
          <p className="muted">
            Reminders, recurring reports, integration syncs, approval gates, retries, and dead letters.
          </p>
          {temporal ? (
            <p className="muted">
              Temporal {temporal.address} · queue {temporal.task_queue}
              {temporal.use_worker_dispatch ? ' · worker dispatch on' : ''}
            </p>
          ) : null}
        </div>
        <div className="button-row">
          <Button variant="outline" onClick={refresh}>Refresh</Button>
          <Button variant="outline" onClick={runDue}>Run due</Button>
          <Button variant="outline" onClick={createApprovalGate}>Approval gate</Button>
          <Button onClick={createReminder}>Create reminder</Button>
        </div>
      </div>
      <div className="stack">
        {automations.length ? (
          automations.map((automation) => (
            <div className="stat" key={automation.id}>
              <div className="row">
                <div>
                  <strong>{automation.name}</strong>
                  <p className="muted">
                    {automation.type} · {automation.run_count} run(s)
                    {automation.next_run_at ? ` · next ${automation.next_run_at}` : ''}
                  </p>
                </div>
                <div className="button-row">
                  <StatusBadge status={automation.status} />
                  {automation.status === 'waiting_approval' ? (
                    <Button variant="outline" onClick={() => approveAutomation(automation.id)}>Approve</Button>
                  ) : null}
                  {automation.status === 'dead_letter' ? (
                    <Button variant="outline" onClick={() => retryAutomation(automation.id)}>Retry</Button>
                  ) : (
                    <Button variant="outline" onClick={() => runAutomation(automation.id)}>Run</Button>
                  )}
                </div>
              </div>
            </div>
          ))
        ) : (
          <p className="muted">No automations yet.</p>
        )}
        {runs.length ? (
          <div className="stack">
            <div className="eyebrow">Recent runs</div>
            {runs.map((entry, index) => (
              <div className="stat" key={`${entry.automation_id}-${index}`}>
                <strong>{entry.automation_id}</strong>
                <p className="muted">{entry.status}{entry.created_at ? ` · ${entry.created_at}` : ''}</p>
              </div>
            ))}
          </div>
        ) : null}
        {deadLetters.length ? (
          <div className="stack">
            <div className="eyebrow">Dead letter queue</div>
            {deadLetters.map((entry, index) => (
              <div className="stat" key={`${entry.automation_id}-${index}`}>
                <strong>{entry.automation_id}</strong>
                <p className="muted">
                  attempt {entry.attempt ?? 1} · {entry.error || entry.status}
                </p>
              </div>
            ))}
          </div>
        ) : null}
        {message ? <p className="muted">{message}</p> : null}
      </div>
    </Card>
  );
}
