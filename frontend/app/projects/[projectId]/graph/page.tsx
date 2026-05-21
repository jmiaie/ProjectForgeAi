import Link from 'next/link';
import ProjectGraph from '@/components/ProjectGraph';

type PageProps = {
  params: Promise<{ projectId: string }>;
};

export default async function ProjectGraphPage({ params }: PageProps) {
  const { projectId } = await params;

  return (
    <main className="min-h-screen bg-slate-100 py-10">
      <div className="mx-auto max-w-6xl px-4">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Project graph</h1>
            <p className="text-sm text-slate-500">{projectId}</p>
          </div>
          <Link href="/projects" className="text-sm text-slate-600 underline">
            All projects
          </Link>
        </div>
        <ProjectGraph projectId={projectId} />
      </div>
    </main>
  );
}
