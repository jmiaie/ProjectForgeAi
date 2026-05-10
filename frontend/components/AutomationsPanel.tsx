'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { StatusBadge } from '@/components/StatusBadge';
import { apiGet, apiPost, type AutomationRecord } from '@/lib/api';

type AutomationsPanelProps = {
  projectId: string;
  initialAutomations: AutomationRecord[];
};

export function AutomationsPanel({ projectId, initialAutomations }: AutomationsPanelProps) {
  const [automations, setAutomations] = useState(initialAutomations);
  const [message, setMessage] = useState('');

  const refresh = async () => {
    const result = await apiGet<{ automations: AutomationRecord[] }>(
      `/api/v1/projects/${projectId}/automations`,
    );
    setAutomations(result.automations);
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
    const result = await apiPost<{ status: string }>(
      `/api/v1/projects/${projectId}/automations/${automationId}/run`,
      {},
    );
    setMessage(`Run finished with ${result.status}.`);
    await refresh();
  };

  return (
    <Card className="panel">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Durable Workflows</div>
          <h2>Automations</h2>
          <p className="muted">Reminders, recurring reports, integration syncs, and approval gates.</p>
        </div>
        <div className="row">
          <Button variant="outline" onClick={refresh}>Refresh</Button>
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
                <div className="row">
                  <StatusBadge status={automation.status} />
                  <Button variant="outline" onClick={() => runAutomation(automation.id)}>Run</Button>
                </div>
              </div>
            </div>
          ))
        ) : (
          <p className="muted">No automations yet.</p>
        )}
        {message ? <p className="muted">{message}</p> : null}
      </div>
    </Card>
  );
}
