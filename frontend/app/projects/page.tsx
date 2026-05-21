'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { apiFetch, type ProjectSummary } from '@/lib/api';

type ProjectListResponse = {
  items: Array<{
    id: string;
    name: string;
    status: string;
    compliance: string;
  }>;
};

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<ProjectListResponse>('/api/v1/projects/')
      .then((data) =>
        setProjects(
          data.items.map((p) => ({
            id: p.id,
            name: p.name,
            status: p.status,
            compliance: p.compliance,
          })),
        ),
      )
      .catch((err) => setError(err instanceof Error ? err.message : 'Load failed'));
  }, []);

  return (
    <main className="min-h-screen bg-slate-100 py-10">
      <div className="mx-auto max-w-4xl px-4">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-3xl font-bold text-slate-900">Projects</h1>
          <Link href="/" className="text-sm text-slate-600 underline">
            Home
          </Link>
        </div>
        {error && (
          <p className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-800">
            {error}
          </p>
        )}
        <ul className="space-y-3">
          {projects.map((p) => (
            <li
              key={p.id}
              className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
            >
              <div>
                <p className="font-medium text-slate-900">{p.name}</p>
                <p className="text-sm text-slate-500">
                  {p.id} · {p.status} · {p.compliance}
                </p>
              </div>
              <Link
                href={`/projects/${p.id}/graph`}
                className="rounded bg-indigo-600 px-3 py-1 text-sm text-white"
              >
                View graph
              </Link>
            </li>
          ))}
        </ul>
        {!error && projects.length === 0 && (
          <p className="text-slate-600">
            No projects yet. Create one via the intake wizard on the home page.
          </p>
        )}
      </div>
    </main>
  );
}
