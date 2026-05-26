import { ExecutiveDashboardPanel } from '@/components/ExecutiveDashboardPanel';
import { PortfolioPanel } from '@/components/PortfolioPanel';
import { TenantBillingPanel } from '@/components/TenantBillingPanel';
import { ProjectSwitcher } from '@/components/ProjectSwitcher';
import { apiGet, defaultProjectId } from '@/lib/api';

export default async function PortfolioPage({
  searchParams,
}: {
  searchParams?: Promise<{ projectId?: string }>;
}) {
  const params = await searchParams;
  const projectId = params?.projectId || defaultProjectId();
  const summary = await apiGet<{ totals: { projects: number; nodes: number; edges: number } }>(
    '/api/v1/portfolio/summary',
  ).catch(() => undefined);

  return (
    <main className="app-shell">
      <div className="container">
        <header className="topbar">
          <div className="brand">
            <span className="eyebrow">ProjectForge AI</span>
            <h1>Portfolio</h1>
            <p className="muted">Manage projects across your workspace.</p>
          </div>
          <ProjectSwitcher activeProjectId={projectId} />
        </header>
        <div className="stack">
          {summary ? (
            <p className="muted">
              {summary.totals.projects} project(s) · {summary.totals.nodes} nodes ·{' '}
              {summary.totals.edges} edges
            </p>
          ) : null}
          <ExecutiveDashboardPanel />
          <TenantBillingPanel tenantId={process.env.NEXT_PUBLIC_TENANT_ID || 'tenant_default'} />
          <PortfolioPanel activeProjectId={projectId} />
        </div>
      </div>
    </main>
  );
}
