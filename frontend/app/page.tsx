import { AccessPanel } from '@/components/AccessPanel';
import { AutomationsPanel } from '@/components/AutomationsPanel';
import { CompliancePanel } from '@/components/CompliancePanel';
import { ConnectionsPanel } from '@/components/ConnectionsPanel';
import { GraphPanel } from '@/components/GraphPanel';
import { IngestionPanel } from '@/components/IngestionPanel';
import { LLMPanel } from '@/components/LLMPanel';
import { OrchestratorPanel } from '@/components/OrchestratorPanel';
import { PortfolioPanel } from '@/components/PortfolioPanel';
import { ProjectSummaryCards } from '@/components/ProjectSummaryCards';
import { ProjectSwitcher } from '@/components/ProjectSwitcher';
import { WorkbenchPanel } from '@/components/WorkbenchPanel';
import {
  apiGet,
  defaultProjectId,
  type ComplianceProfile,
  type AutomationRecord,
  type ConnectionRecord,
  type GraphStatus,
  type HealthResponse,
} from '@/lib/api';

async function safeGet<T>(path: string): Promise<T | undefined> {
  try {
    return await apiGet<T>(path);
  } catch {
    return undefined;
  }
}

export default async function Home({
  searchParams,
}: {
  searchParams?: Promise<{ projectId?: string }>;
}) {
  const params = await searchParams;
  const projectId = params?.projectId || defaultProjectId();
  const [health, graph, compliance, connections, automations] = await Promise.all([
    safeGet<HealthResponse>('/health'),
    safeGet<GraphStatus>(`/api/v1/projects/${projectId}/graph/status`),
    safeGet<ComplianceProfile>(`/api/v1/projects/${projectId}/compliance/profile`),
    safeGet<{ connections: ConnectionRecord[] }>(`/api/v1/intake/connections/${projectId}`),
    safeGet<{ automations: AutomationRecord[] }>(`/api/v1/projects/${projectId}/automations`),
  ]);

  return (
    <main className="app-shell">
      <div className="container">
        <header className="topbar">
          <div className="brand">
            <span className="eyebrow">ProjectForge AI</span>
            <h1>Universal Project OS</h1>
            <p className="muted">
              Ingest documents, build a living graph, run specialist agents, and keep controls auditable.
            </p>
          </div>
          <ProjectSwitcher activeProjectId={projectId} />
        </header>

        <div className="stack">
          <PortfolioPanel activeProjectId={projectId} />
          <ProjectSummaryCards
            health={health}
            graph={graph}
            compliance={compliance}
            connectionsCount={connections?.connections.length ?? 0}
          />
          <div className="grid grid-2">
            <IngestionPanel projectId={projectId} />
            <GraphPanel projectId={projectId} initialStatus={graph} />
          </div>
          <div className="grid grid-2">
            <OrchestratorPanel projectId={projectId} />
            <CompliancePanel projectId={projectId} initialProfile={compliance} />
          </div>
          <AccessPanel projectId={projectId} />
          <LLMPanel projectId={projectId} />
          <WorkbenchPanel projectId={projectId} />
          <ConnectionsPanel projectId={projectId} initialConnections={connections?.connections ?? []} />
          <AutomationsPanel projectId={projectId} initialAutomations={automations?.automations ?? []} />
        </div>
      </div>
    </main>
  );
}
