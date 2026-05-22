'use client';

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { apiGet } from '@/lib/api';

type GraphNodeRecord = {
  id: string;
  label: string;
  properties: Record<string, unknown>;
};

type GraphResponse = {
  graph: {
    nodes: GraphNodeRecord[];
  };
};

type TimelinePanelProps = {
  projectId: string;
  refreshKey?: number;
};

export function TimelinePanel({ projectId, refreshKey = 0 }: TimelinePanelProps) {
  const [milestones, setMilestones] = useState<GraphNodeRecord[]>([]);
  const [tasks, setTasks] = useState<GraphNodeRecord[]>([]);

  useEffect(() => {
    apiGet<GraphResponse>(`/api/v1/projects/${projectId}/graph`)
      .then((response) => {
        const nodes = response.graph?.nodes ?? [];
        setMilestones(nodes.filter((node) => node.label === 'Milestone'));
        setTasks(nodes.filter((node) => node.label === 'Task'));
      })
      .catch(() => {
        setMilestones([]);
        setTasks([]);
      });
  }, [projectId, refreshKey]);

  const items = [...milestones, ...tasks].sort(
    (left, right) => Number(left.properties.sequence ?? 99) - Number(right.properties.sequence ?? 99),
  );

  return (
    <Card className="panel">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Timeline</div>
          <h2>Gantt placeholder</h2>
          <p className="muted">Milestone and task nodes from enriched graph facts.</p>
        </div>
      </div>
      {items.length ? (
        <div className="timeline">
          {items.map((item, index) => (
            <div key={item.id} className="timeline-row">
              <div className="timeline-label">
                <strong>{String(item.properties.name ?? item.label)}</strong>
                <span className="muted">{item.label}</span>
              </div>
              <div className="timeline-bar-shell">
                <div
                  className="timeline-bar"
                  style={{ width: `${Math.min(90, 30 + index * 20)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="muted">Enrich the graph to populate milestone and task timeline bars.</p>
      )}
    </Card>
  );
}
