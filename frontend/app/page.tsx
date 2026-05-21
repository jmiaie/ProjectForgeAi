import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="space-y-8">
      <section className="rounded-2xl bg-gradient-to-br from-brand-900 to-brand-700 px-8 py-12 text-white shadow-lg">
        <h1 className="text-4xl font-bold">ProjectForge AI</h1>
        <p className="mt-3 max-w-2xl text-brand-100">
          Upload all project documents once → instant living project graph → auto-generates
          every template, contract, schedule, automation, communication loop, and
          compliance control.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            href="/projects"
            className="rounded-md bg-white px-4 py-2 text-sm font-semibold text-brand-800 hover:bg-brand-50"
          >
            Open dashboard
          </Link>
          <Link
            href="/settings/connections"
            className="rounded-md border border-white/30 px-4 py-2 text-sm font-medium text-white hover:bg-white/10"
          >
            Connect tools
          </Link>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        {[
          {
            title: 'Graph',
            body: 'React Flow visualization of documents, chunks, milestones, risks, and orchestrator artefacts.',
          },
          {
            title: 'Gantt',
            body: 'Schedule view built from Milestone and Task nodes produced by the schedule specialist.',
          },
          {
            title: 'Chat',
            body: 'Grounded Q&A via Locus BM25 retrieval with optional multi-agent orchestration.',
          },
        ].map((card) => (
          <div
            key={card.title}
            className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <h2 className="text-lg font-semibold text-slate-900">{card.title}</h2>
            <p className="mt-2 text-sm text-slate-600">{card.body}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
