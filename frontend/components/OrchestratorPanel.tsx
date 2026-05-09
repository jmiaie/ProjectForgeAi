'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { apiPost, type OrchestratorRun } from '@/lib/api';
import { StatusBadge } from '@/components/StatusBadge';

type OrchestratorPanelProps = {
  projectId: string;
};

export function OrchestratorPanel({ projectId }: OrchestratorPanelProps) {
  const [goal, setGoal] = useState('Create project operating plan');
  const [run, setRun] = useState<OrchestratorRun | undefined>();
  const [error, setError] = useState('');

  const runWorkflow = async () => {
    setError('');
    try {
      const result = await apiPost<OrchestratorRun>('/api/v1/orchestrator/run', {
        project_id: projectId,
        goal,
      });
      setRun(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to run orchestrator');
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
        <Button onClick={runWorkflow}>Run orchestrator</Button>
        {error ? <p className="badge badge-warning">{error}</p> : null}
        {run ? (
          <div className="stack">
            {run.steps.map((step) => (
              <div className="stat" key={step.name}>
                <div className="row">
                  <strong>{step.name.replace('_', ' ')}</strong>
                  <StatusBadge status={step.status} />
                </div>
                <p className="muted">{step.summary}</p>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </Card>
  );
}
