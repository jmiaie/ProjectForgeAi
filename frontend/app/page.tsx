import IntakeWizard from '@/components/IntakeWizard';

export default function HomePage() {
  return (
    <main className="min-h-screen bg-slate-100 py-12">
      <div className="mx-auto max-w-3xl px-4">
        <h1 className="mb-2 text-4xl font-bold text-slate-900">ProjectForge AI</h1>
        <p className="mb-8 text-slate-600">
          Upload all project documents once &rarr; instant living project graph.
        </p>
        <IntakeWizard />
      </div>
    </main>
  );
}
