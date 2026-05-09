'use client';

import { useCallback, useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

type DashboardPayload = {
  status: string;
  project_id: string;
  metrics: {
    connections: number;
    graph_nodes: number;
    graph_edges: number;
    workflow_steps_completed: number;
    audit_events: number;
    scheduled_jobs?: number;
    reports_generated?: number;
  };
  compliance: {
    category: string;
    last_updated: string | null;
  };
  workflow: {
    status?: string;
    current_stage?: string;
    states_visited?: string[];
  };
  graph_summary: {
    status?: string;
    nodes?: number;
    edges?: number;
    backend?: string;
  };
  state_store_backend?: string;
  scheduler_backend?: string;
  connections: Array<{
    connector?: string;
    type?: string;
    status?: string;
    connected_at?: string;
  }>;
  workflow_jobs?: Array<{
    job_id: string;
    name: string;
    job_type: string;
    schedule_type: string;
    next_run_at?: string | null;
    enabled: boolean;
  }>;
  reports?: Array<{
    report_id: string;
    type: string;
    generated_at: string;
    source: string;
    summary: string;
  }>;
  recent_events: Array<{
    event_type: string;
    timestamp: string;
    payload: Record<string, unknown>;
  }>;
};

const projectId = 'proj_123';

export default function DashboardPage() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [operationStatus, setOperationStatus] = useState<string>('');
  const [jobName, setJobName] = useState<string>('Dashboard Weekly Report');
  const [scheduleType, setScheduleType] = useState<'once' | 'hourly' | 'daily' | 'weekly'>('weekly');
  const [intervalMinutes, setIntervalMinutes] = useState<string>('60');

  const loadDashboard = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const response = await fetch(`/api/v1/projects/${projectId}/dashboard`);
      if (!response.ok) {
        const message = await response.text();
        setError(`Dashboard request failed: ${message}`);
        return;
      }
      const payload: DashboardPayload = await response.json();
      setData(payload);
    } catch (err) {
      setError(`Dashboard request failed: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  const runTick = useCallback(async () => {
    setOperationStatus('Running workflow tick...');
    const response = await fetch(`/api/v1/projects/${projectId}/workflows/tick`, { method: 'POST' });
    const payload = await response.json();
    if (!response.ok) {
      setOperationStatus(`Workflow tick failed: ${payload.detail ?? 'unknown error'}`);
      return;
    }
    setOperationStatus(`Workflow tick executed ${payload.executed} due job(s).`);
    await loadDashboard();
  }, [loadDashboard]);

  const generateReport = useCallback(async () => {
    setOperationStatus('Generating weekly status report...');
    const response = await fetch(`/api/v1/projects/${projectId}/reports/weekly-status`, { method: 'POST' });
    const payload = await response.json();
    if (!response.ok) {
      setOperationStatus(`Report generation failed: ${payload.detail ?? 'unknown error'}`);
      return;
    }
    setOperationStatus(`Generated report ${payload.report?.report_id ?? 'unknown'}.`);
    await loadDashboard();
  }, [loadDashboard]);

  const createWorkflowJob = useCallback(async () => {
    setOperationStatus('Scheduling workflow job...');
    const body: Record<string, unknown> = {
      name: jobName,
      job_type: 'weekly_status_report',
      schedule_type: scheduleType,
      payload: { source: 'dashboard' },
    };
    if (scheduleType !== 'once') {
      body.interval_minutes = Number(intervalMinutes);
    }

    const response = await fetch(`/api/v1/projects/${projectId}/workflows/jobs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const payload = await response.json();
    if (!response.ok) {
      setOperationStatus(`Schedule failed: ${payload.detail ?? 'unknown error'}`);
      return;
    }
    setOperationStatus(`Scheduled job ${payload.job?.job_id ?? 'unknown'}.`);
    await loadDashboard();
  }, [intervalMinutes, jobName, loadDashboard, scheduleType]);

  const runJob = useCallback(
    async (jobId: string) => {
      setOperationStatus(`Running job ${jobId}...`);
      const response = await fetch(`/api/v1/projects/${projectId}/workflows/jobs/${jobId}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const payload = await response.json();
      if (!response.ok) {
        setOperationStatus(`Run failed: ${payload.detail ?? 'unknown error'}`);
        return;
      }
      setOperationStatus(`Executed run ${payload.run?.run_id ?? 'unknown'}.`);
      await loadDashboard();
    },
    [loadDashboard]
  );

  const toggleJobEnabled = useCallback(
    async (jobId: string, enabled: boolean) => {
      setOperationStatus(`${enabled ? 'Enabling' : 'Disabling'} job ${jobId}...`);
      const response = await fetch(`/api/v1/projects/${projectId}/workflows/jobs/${jobId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      });
      const payload = await response.json();
      if (!response.ok) {
        setOperationStatus(`Update failed: ${payload.detail ?? 'unknown error'}`);
        return;
      }
      setOperationStatus(`Job ${jobId} ${enabled ? 'enabled' : 'disabled'}.`);
      await loadDashboard();
    },
    [loadDashboard]
  );

  const deleteJob = useCallback(
    async (jobId: string) => {
      setOperationStatus(`Deleting job ${jobId}...`);
      const response = await fetch(`/api/v1/projects/${projectId}/workflows/jobs/${jobId}`, {
        method: 'DELETE',
      });
      const payload = await response.json();
      if (!response.ok) {
        setOperationStatus(`Delete failed: ${payload.detail ?? 'unknown error'}`);
        return;
      }
      setOperationStatus(`Deleted job ${payload.job_id ?? jobId}.`);
      await loadDashboard();
    },
    [loadDashboard]
  );

  const metricCards = [
    { label: 'Connections', value: data?.metrics.connections ?? 0 },
    { label: 'Graph Nodes', value: data?.metrics.graph_nodes ?? 0 },
    { label: 'Graph Edges', value: data?.metrics.graph_edges ?? 0 },
    { label: 'Workflow Steps', value: data?.metrics.workflow_steps_completed ?? 0 },
    { label: 'Audit Events', value: data?.metrics.audit_events ?? 0 },
    { label: 'Scheduled Jobs', value: data?.metrics.scheduled_jobs ?? 0 },
    { label: 'Reports', value: data?.metrics.reports_generated ?? 0 },
  ];

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">ProjectForge Dashboard</h1>
          <p className="text-sm text-slate-600">
            Project: {projectId} {data ? `• Compliance: ${data.compliance.category}` : ''}
          </p>
        </div>
        <Button onClick={() => void loadDashboard()} variant="outline">
          Refresh
        </Button>
      </div>

      {loading ? <p className="text-sm text-slate-600">Loading dashboard...</p> : null}
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      {operationStatus ? <p className="text-sm text-indigo-700">{operationStatus}</p> : null}

      <section className="grid grid-cols-1 gap-4 md:grid-cols-7">
        {metricCards.map((metric) => (
          <Card key={metric.label} className="p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">{metric.label}</p>
            <p className="mt-2 text-2xl font-semibold">{metric.value}</p>
          </Card>
        ))}
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <h2 className="text-lg font-semibold">Workflow</h2>
          <p className="mt-2 text-sm text-slate-700">
            Status: {data?.workflow.status ?? 'unknown'} • Current stage:{' '}
            {data?.workflow.current_stage ?? 'unknown'}
          </p>
          <ul className="mt-3 list-disc pl-5 text-sm text-slate-700">
            {(data?.workflow.states_visited ?? []).map((stage) => (
              <li key={stage}>{stage}</li>
            ))}
          </ul>
        </Card>

        <Card className="p-5">
          <h2 className="text-lg font-semibold">Graph Summary</h2>
          <p className="mt-2 text-sm text-slate-700">
            Nodes: {data?.graph_summary.nodes ?? 0} • Edges: {data?.graph_summary.edges ?? 0}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Backend: {data?.graph_summary.backend ?? 'unknown'}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            State store: {data?.state_store_backend ?? 'unknown'} • Scheduler: {data?.scheduler_backend ?? 'unknown'}
          </p>
        </Card>
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <h2 className="text-lg font-semibold">Automation Controls</h2>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            <Button onClick={() => void runTick()} variant="outline">
              Run Workflow Tick
            </Button>
            <Button onClick={() => void generateReport()} variant="outline">
              Generate Weekly Report
            </Button>
          </div>
          <div className="mt-4 space-y-2">
            <label className="block text-xs font-medium uppercase tracking-wide text-slate-500">
              Job Name
            </label>
            <input
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              value={jobName}
              onChange={(event) => setJobName(event.target.value)}
            />
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
              <div>
                <label className="block text-xs font-medium uppercase tracking-wide text-slate-500">
                  Schedule Type
                </label>
                <select
                  className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                  value={scheduleType}
                  onChange={(event) =>
                    setScheduleType(event.target.value as 'once' | 'hourly' | 'daily' | 'weekly')
                  }
                >
                  <option value="once">once</option>
                  <option value="hourly">hourly</option>
                  <option value="daily">daily</option>
                  <option value="weekly">weekly</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium uppercase tracking-wide text-slate-500">
                  Interval Minutes
                </label>
                <input
                  className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                  value={intervalMinutes}
                  onChange={(event) => setIntervalMinutes(event.target.value)}
                  disabled={scheduleType === 'once'}
                />
              </div>
            </div>
            <Button onClick={() => void createWorkflowJob()} className="w-full">
              Create Scheduled Job
            </Button>
          </div>
        </Card>

        <Card className="p-5">
          <h2 className="text-lg font-semibold">Connections</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {(data?.connections ?? []).map((connection, index) => (
              <li key={`${connection.connector ?? 'connector'}-${index}`} className="rounded border p-2">
                <p>
                  <span className="font-medium">{connection.connector}</span> ({connection.type})
                </p>
                <p className="text-slate-600">
                  Status: {connection.status} • {connection.connected_at ?? 'n/a'}
                </p>
              </li>
            ))}
            {(data?.connections?.length ?? 0) === 0 ? (
              <li className="text-slate-500">No connections recorded yet.</li>
            ) : null}
          </ul>
        </Card>

        <Card className="p-5">
          <h2 className="text-lg font-semibold">Recent Audit Events</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {(data?.recent_events ?? []).map((event, index) => (
              <li key={`${event.event_type}-${event.timestamp}-${index}`} className="rounded border p-2">
                <p className="font-medium">{event.event_type}</p>
                <p className="text-xs text-slate-500">{event.timestamp}</p>
              </li>
            ))}
            {(data?.recent_events?.length ?? 0) === 0 ? (
              <li className="text-slate-500">No audit events recorded yet.</li>
            ) : null}
          </ul>
        </Card>
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <h2 className="text-lg font-semibold">Scheduled Workflow Jobs</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {(data?.workflow_jobs ?? []).map((job) => (
              <li key={job.job_id} className="rounded border p-2">
                <p>
                  <span className="font-medium">{job.name}</span> ({job.job_type})
                </p>
                <p className="text-slate-600">
                  Schedule: {job.schedule_type} • Next run: {job.next_run_at ?? 'n/a'} •{' '}
                  {job.enabled ? 'enabled' : 'disabled'}
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button variant="outline" onClick={() => void runJob(job.job_id)}>
                    Run Now
                  </Button>
                  <Button variant="outline" onClick={() => void toggleJobEnabled(job.job_id, !job.enabled)}>
                    {job.enabled ? 'Disable' : 'Enable'}
                  </Button>
                  <Button variant="outline" onClick={() => void deleteJob(job.job_id)}>
                    Delete
                  </Button>
                </div>
              </li>
            ))}
            {(data?.workflow_jobs?.length ?? 0) === 0 ? (
              <li className="text-slate-500">No workflow jobs scheduled yet.</li>
            ) : null}
          </ul>
        </Card>

        <Card className="p-5">
          <h2 className="text-lg font-semibold">Generated Reports</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {(data?.reports ?? []).map((report) => (
              <li key={report.report_id} className="rounded border p-2">
                <p className="font-medium">{report.type}</p>
                <p className="text-slate-600">
                  Source: {report.source} • {report.generated_at}
                </p>
                <p className="text-slate-700">{report.summary}</p>
              </li>
            ))}
            {(data?.reports?.length ?? 0) === 0 ? (
              <li className="text-slate-500">No reports generated yet.</li>
            ) : null}
          </ul>
        </Card>
      </section>
    </main>
  );
}
