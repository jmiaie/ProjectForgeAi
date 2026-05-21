import IntakeWizard from '@/components/IntakeWizard';
import AuthPanel from '@/components/AuthPanel';
import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="min-h-screen py-12">
      <div className="mx-auto grid max-w-5xl gap-8 px-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <h1 className="mb-2 text-4xl font-bold text-slate-900">ProjectForge AI</h1>
          <p className="mb-4 text-slate-600">
            Upload documents, orchestrate agents, and explore the living project graph.
          </p>
          <p className="mb-8">
            <Link href="/projects" className="text-indigo-600 underline">
              View all projects →
            </Link>
          </p>
          <IntakeWizard />
        </div>
        <div>
          <AuthPanel />
        </div>
      </div>
    </main>
  );
}
