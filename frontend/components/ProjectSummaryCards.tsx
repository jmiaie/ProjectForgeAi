import type { ComplianceProfile, GraphStatus, HealthResponse } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { StatusBadge } from '@/components/StatusBadge';

type ProjectSummaryCardsProps = {
  health?: HealthResponse;
  graph?: GraphStatus;
  compliance?: ComplianceProfile;
  connectionsCount: number;
};

export function ProjectSummaryCards({
  health,
  graph,
  compliance,
  connectionsCount,
}: ProjectSummaryCardsProps) {
  return (
    <div className="grid grid-3">
      <Card className="panel">
        <div className="panel-header">
          <div>
            <div className="eyebrow">Backend</div>
            <h3>Runtime</h3>
          </div>
          {health ? <StatusBadge status={health.status} /> : <StatusBadge status="pending" />}
        </div>
        <p className="muted">Default model</p>
        <strong>{health?.llm_default || 'Waiting for backend'}</strong>
      </Card>
      <Card className="panel">
        <div className="panel-header">
          <div>
            <div className="eyebrow">Graph</div>
            <h3>Project Map</h3>
          </div>
          <StatusBadge status={Boolean(graph?.built)} />
        </div>
        <div className="grid grid-2">
          <div className="stat">
            <div className="stat-value">{graph?.node_count ?? 0}</div>
            <span className="muted">nodes</span>
          </div>
          <div className="stat">
            <div className="stat-value">{graph?.edge_count ?? 0}</div>
            <span className="muted">edges</span>
          </div>
        </div>
      </Card>
      <Card className="panel">
        <div className="panel-header">
          <div>
            <div className="eyebrow">Controls</div>
            <h3>Compliance + Tools</h3>
          </div>
          <StatusBadge status={compliance?.category || 'standard'} />
        </div>
        <p className="muted">{connectionsCount} connected integration(s)</p>
        <p className="muted">
          Memory writes {compliance?.allow_memory_writes === false ? 'gated' : 'allowed'}
        </p>
      </Card>
    </div>
  );
}
