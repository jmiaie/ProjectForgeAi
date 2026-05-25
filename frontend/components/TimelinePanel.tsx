'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { apiGet, apiPatch } from '@/lib/api';

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
  onGraphChanged?: () => void;
};

export function TimelinePanel({ projectId, refreshKey = 0, onGraphChanged }: TimelinePanelProps) {
  const [milestones, setMilestones] = useState<GraphNodeRecord[]>([]);
  const [tasks, setTasks] = useState<GraphNodeRecord[]>([]);
  const [message, setMessage] = useState('');

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

  const saveDates = async (item: GraphNodeRecord, startDate: string, dueDate: string) => {
    await apiPatch(`/api/v1/projects/${projectId}/graph/nodes/${item.id}`, {
      properties: {
        start_date: startDate || undefined,
        due_date: dueDate || undefined,
      },
    });
    setMessage(`Updated dates for ${String(item.properties.name ?? item.label)}.`);
    onGraphChanged?.();
  };

  return (
    <Card className="panel">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Timeline</div>
          <h2>Gantt timeline</h2>
          <p className="muted">Edit milestone and task dates stored on graph nodes.</p>
        </div>
      </div>
      {items.length ? (
        <div className="timeline">
          {items.map((item, index) => (
            <TimelineRow key={item.id} item={item} index={index} onSave={saveDates} />
          ))}
        </div>
      ) : (
        <p className="muted">Enrich the graph to populate milestone and task timeline bars.</p>
      )}
      {message ? <p className="muted">{message}</p> : null}
    </Card>
  );
}

function TimelineRow({
  item,
  index,
  onSave,
}: {
  item: GraphNodeRecord;
  index: number;
  onSave: (item: GraphNodeRecord, startDate: string, dueDate: string) => Promise<void>;
}) {
  const [startDate, setStartDate] = useState(String(item.properties.start_date ?? ''));
  const [dueDate, setDueDate] = useState(String(item.properties.due_date ?? ''));
  const [saving, setSaving] = useState(false);

  return (
    <div className="timeline-row">
      <div className="timeline-label">
        <strong>{String(item.properties.name ?? item.label)}</strong>
        <span className="muted">{item.label}</span>
        <div className="button-row">
          <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
          <input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} />
          <Button
            variant="outline"
            disabled={saving}
            onClick={async () => {
              setSaving(true);
              try {
                await onSave(item, startDate, dueDate);
              } finally {
                setSaving(false);
              }
            }}
          >
            Save
          </Button>
        </div>
      </div>
      <div className="timeline-bar-shell">
        <div className="timeline-bar" style={{ width: `${Math.min(90, 30 + index * 20)}%` }} />
      </div>
    </div>
  );
}
