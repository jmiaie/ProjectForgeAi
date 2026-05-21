'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import CreateProjectForm from '@/components/dashboard/CreateProjectForm';
import { listProjects, type Project } from '@/lib/api';
import { useAuth } from '@/lib/auth';

export default function ProjectsPage() {
  const { token } = useAuth();
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const payload = await listProjects(token);
        if (!cancelled) setProjects(payload.items);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load projects');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Projects</h1>
        <p className="mt-1 text-slate-600">
          Living project graphs with graph view, Gantt schedule, and grounded chat.
        </p>
      </div>

      <CreateProjectForm
        onCreated={(projectId) => {
          router.push(`/projects/${projectId}`);
        }}
      />

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Your projects</h2>
        {loading && <p className="mt-4 text-sm text-slate-500">Loading…</p>}
        {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
        {!loading && !error && projects.length === 0 && (
          <p className="mt-4 text-sm text-slate-500">No projects yet. Create one above.</p>
        )}
        <ul className="mt-4 divide-y divide-slate-100">
          {projects.map((project) => (
            <li key={project.id} className="flex items-center justify-between py-3">
              <div>
                <Link
                  href={`/projects/${project.id}`}
                  className="font-medium text-brand-700 hover:underline"
                >
                  {project.name}
                </Link>
                <p className="text-xs text-slate-500">
                  {project.id} · {project.status} · {project.compliance}
                </p>
              </div>
              <Link
                href={`/projects/${project.id}`}
                className="rounded-md border border-slate-200 px-3 py-1.5 text-sm hover:bg-slate-50"
              >
                Open dashboard
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
