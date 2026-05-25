'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { apiGet, apiPost } from '@/lib/api';
import { StatusBadge } from '@/components/StatusBadge';

export type PortfolioProjectSummary = {
  project_id: string;
  name: string;
  status: string;
  tier: string;
  compliance: string;
  graph_built: boolean;
  node_count: number;
  edge_count: number;
  updated_at: string;
};

type PortfolioSummary = {
  totals: {
    projects: number;
    nodes: number;
    edges: number;
    archived: number;
  };
  projects: PortfolioProjectSummary[];
};

type PortfolioPanelProps = {
  activeProjectId: string;
};

export function PortfolioPanel({ activeProjectId }: PortfolioPanelProps) {
  const [summary, setSummary] = useState<PortfolioSummary | undefined>();
  const [name, setName] = useState('');
  const [compliance, setCompliance] = useState('standard');
  const [message, setMessage] = useState('');

  const refresh = async () => {
    const result = await apiGet<PortfolioSummary>('/api/v1/portfolio/summary');
    setSummary(result);
  };

  useEffect(() => {
    refresh().catch(() => undefined);
  }, []);

  const createProject = async () => {
    if (!name.trim()) {
      setMessage('Enter a project name.');
      return;
    }
    const result = await apiPost<{ project: { project_id: string } }>(
      '/api/v1/projects/register',
      { name, compliance },
    );
    setMessage(`Created ${result.project.project_id}`);
    setName('');
    await refresh();
    window.location.href = `/?projectId=${encodeURIComponent(result.project.project_id)}`;
  };

  const archiveProject = async (projectId: string) => {
    await apiPost(`/api/v1/projects/${projectId}/archive`, {});
    setMessage(`Archived ${projectId}`);
    await refresh();
  };

  return (
    <Card className="panel">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Portfolio</div>
          <h2>Multi-project workspace</h2>
          <p className="muted">Cross-project graph totals and quick project switching.</p>
        </div>
        <Button variant="outline" onClick={refresh}>Refresh</Button>
      </div>
      {summary ? (
        <div className="stack">
          <div className="grid grid-3">
            <div className="stat">
              <div className="stat-value">{summary.totals.projects}</div>
              <span className="muted">active projects</span>
            </div>
            <div className="stat">
              <div className="stat-value">{summary.totals.nodes}</div>
              <span className="muted">total nodes</span>
            </div>
            <div className="stat">
              <div className="stat-value">{summary.totals.edges}</div>
              <span className="muted">total edges</span>
            </div>
          </div>
          <div className="button-row">
            <input
              className="input"
              placeholder="New project name"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
            <select
              className="input"
              value={compliance}
              onChange={(event) => setCompliance(event.target.value)}
              aria-label="Compliance profile"
            >
              <option value="standard">standard</option>
              <option value="hipaa">hipaa</option>
              <option value="legal">legal</option>
              <option value="soc2">soc2</option>
              <option value="gdpr">gdpr</option>
            </select>
            <Button onClick={createProject}>Create project</Button>
          </div>
          {summary.projects.map((project) => (
            <div className="stat" key={project.project_id}>
              <div className="row">
                <div>
                  <strong>{project.name}</strong>
                  <p className="muted">
                    {project.project_id} · {project.compliance} · {project.tier} · {project.node_count} nodes
                  </p>
                </div>
                <div className="row">
                  {project.project_id === activeProjectId ? (
                    <StatusBadge status="active" />
                  ) : (
                    <Link href={`/?projectId=${encodeURIComponent(project.project_id)}`}>
                      <Button variant="outline">Open</Button>
                    </Link>
                  )}
                  {project.project_id !== activeProjectId ? (
                    <Button variant="outline" onClick={() => archiveProject(project.project_id)}>
                      Archive
                    </Button>
                  ) : null}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="muted">Loading portfolio summary…</p>
      )}
      {message ? <p className="muted">{message}</p> : null}
    </Card>
  );
}
