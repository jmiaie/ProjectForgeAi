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
};

type AutomationsPanelProps = {
  projectId: string;
  initialAutomations: AutomationRecord[];
};

export function AutomationsPanel({ projectId, initialAutomations }: AutomationsPanelProps) {
  const [automations, setAutomations] = useState(initialAutomations);
  const [deadLetters, setDeadLetters] = useState<AutomationRun[]>([]);
  const [message, setMessage] = useState('');

  const refresh = async () => {
    const [items, deadLetterItems] = await Promise.all([
      apiGet<{ automations: AutomationRecord[] }>(`/api/v1/projects/${projectId}/automations`),
      apiGet<{ dead_letters: AutomationRun[] }>(`/api/v1/projects/${projectId}/automations/dead-letters`),
    ]);
    setAutomations(items.automations);
    setDeadLetters(deadLetterItems.dead_letters);
  };

  const createReminder = async () => {
    const result = await apiPost<AutomationRecord>(`/api/v1/projects/${projectId}/automations`, {
      type: 'timed_reminder',
      name: 'Review project plan',
      payload: { message: 'Review the latest ProjectForge operating plan', recipient: 'project_owner' },
    });
    setMessage(`Created ${result.name}.`);
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
    const result = await apiPost<{ processed: number }>(`/api/v1/automations/temporal/run-due`, {});
    setMessage(`Temporal runner processed ${result.processed} due automation(s).`);
    await refresh();
  };

  return (
    <Card className="panel">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Durable Workflows</div>
          <h2>Automations</h2>
          <p className="muted">Reminders, recurring reports, integration syncs, approval gates, retries, and dead letters.</p>
        </div>
        <div className="button-row">
          <Button variant="outline" onClick={refresh}>Refresh</Button>
          <Button variant="outline" onClick={runDue}>Run due</Button>
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
                  <p className="muted">{automation.type} · {automation.run_count} run(s)</p>
                </div>
                <div className="button-row">
                  <StatusBadge status={automation.status} />
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
