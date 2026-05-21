import Link from 'next/link';

import ProjectDashboard from '@/components/dashboard/ProjectDashboard';

type ProjectPageProps = {
  params: Promise<{ id: string }>;
};

export default async function ProjectPage({ params }: ProjectPageProps) {
  const { id } = await params;

  return (
    <div>
      <div className="mb-6">
        <Link href="/projects" className="text-sm text-brand-700 hover:underline">
          ← All projects
        </Link>
        <p className="mt-2 font-mono text-xs text-slate-500">{id}</p>
      </div>
      <ProjectDashboard projectId={id} />
    </div>
  );
}
