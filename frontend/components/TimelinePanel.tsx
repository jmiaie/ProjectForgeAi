'use client';

import { useEffect, useMemo, useState } from 'react';
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

type TimelineLayout = {
  min: number;
  span: number;
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

  const layout = useMemo(() => computeTimelineLayout(items), [items]);

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
            <TimelineRow key={item.id} item={item} index={index} layout={layout} onSave={saveDates} />
          ))}
        </div>
      ) : (
        <p className="muted">Enrich the graph to populate milestone and task timeline bars.</p>
      )}
      {message ? <p className="muted">{message}</p> : null}
    </Card>
  );
}

function parseDate(value: unknown): Date | null {
  if (typeof value !== 'string' || !value) {
    return null;
  }
  const parsed = new Date(`${value}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function computeTimelineLayout(items: GraphNodeRecord[]): TimelineLayout | null {
  const timestamps: number[] = [];

  for (const item of items) {
    const start = parseDate(item.properties.start_date);
    const end = parseDate(item.properties.due_date);
    if (start) {
      timestamps.push(start.getTime());
    }
    if (end) {
      timestamps.push(end.getTime());
    }
  }

  if (!timestamps.length) {
    return null;
  }

  const min = Math.min(...timestamps);
  const max = Math.max(...timestamps);
  const oneDayMs = 24 * 60 * 60 * 1000;
  return { min, span: Math.max(max - min, oneDayMs) };
}

function barStyle(item: GraphNodeRecord, layout: TimelineLayout | null, index: number) {
  if (!layout) {
    return { width: `${Math.min(90, 30 + index * 20)}%`, marginLeft: '0%' };
  }

  const start = parseDate(item.properties.start_date);
  const end = parseDate(item.properties.due_date);
  const anchorStart = start ?? end;
  const anchorEnd = end ?? start;

  if (!anchorStart || !anchorEnd) {
    return { width: '12%', marginLeft: `${Math.min(85, index * 12)}%` };
  }

  const startMs = anchorStart.getTime();
  const endMs = Math.max(anchorEnd.getTime(), startMs);
  const left = ((startMs - layout.min) / layout.span) * 100;
  const width = Math.max(((endMs - startMs) / layout.span) * 100, 4);

  return {
    marginLeft: `${Math.min(left, 96)}%`,
    width: `${Math.min(width, 100 - left)}%`,
  };
}

function TimelineRow({
  item,
  index,
  layout,
  onSave,
}: {
  item: GraphNodeRecord;
  index: number;
  layout: TimelineLayout | null;
  onSave: (item: GraphNodeRecord, startDate: string, dueDate: string) => Promise<void>;
}) {
  const [startDate, setStartDate] = useState(String(item.properties.start_date ?? ''));
  const [dueDate, setDueDate] = useState(String(item.properties.due_date ?? ''));
  const [saving, setSaving] = useState(false);
  const style = barStyle(item, layout, index);

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
        <div className="timeline-bar" style={style} />
      </div>
    </div>
  );
}
