'use client';

import { useEffect, useState } from 'react';

import {
  fetchGraphStats,
  fetchMemoryStats,
  fetchProject,
  type GraphStats,
  type MemoryStats,
  type Project,
} from '@/lib/api';
import { useAuth } from '@/lib/auth';

type ProjectOverviewProps = {
  projectId: string;
};

export default function ProjectOverview({ projectId }: ProjectOverviewProps) {
  const { token } = useAuth();
  const [project, setProject] = useState<Project | null>(null);
  const [graphStats, setGraphStats] = useState<GraphStats | null>(null);
  const [memoryStats, setMemoryStats] = useState<MemoryStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [proj, graph, memory] = await Promise.all([
          fetchProject(projectId, token),
          fetchGraphStats(projectId),
          fetchMemoryStats(projectId),
        ]);
        if (!cancelled) {
          setProject(proj);
          setGraphStats(graph);
          setMemoryStats(memory);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load overview');
        }
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [projectId, token]);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!project || !graphStats || !memoryStats) {
    return <p className="text-slate-500">Loading overview…</p>;
  }

  const nodeKinds = Object.entries(graphStats.nodes_by_kind ?? {});

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-2xl font-semibold text-slate-900">{project.name}</h2>
        <p className="mt-1 text-sm text-slate-600">
          Status: <span className="font-medium capitalize">{project.status}</span>
          {' · '}
          Compliance: <span className="font-medium uppercase">{project.compliance}</span>
        </p>
        {project.objective && (
          <p className="mt-3 text-sm text-slate-700">{project.objective}</p>
        )}
      </section>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Graph nodes" value={graphStats.total_nodes} />
        <StatCard label="Graph edges" value={graphStats.total_edges} />
        <StatCard
          label="Indexed chunks"
          value={Number(memoryStats.locus?.total_chunks ?? 0)}
        />
        <StatCard
          label="Journal entries"
          value={Number(memoryStats.ompa?.total_entries ?? 0)}
        />
      </div>

      {nodeKinds.length > 0 && (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">Graph composition</h3>
          <div className="mt-4 flex flex-wrap gap-2">
            {nodeKinds.map(([kind, count]) => (
              <span
                key={kind}
                className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700"
              >
                {kind}: {count}
              </span>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-3xl font-bold text-brand-700">{value}</p>
    </div>
  );
}
