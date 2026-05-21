'use client';

import { useEffect, useMemo, useState } from 'react';

import { fetchReactFlow } from '@/lib/api';

type GanttItem = {
  id: string;
  label: string;
  kind: 'Milestone' | 'Task';
  startDay: number;
  durationDays: number;
};

type ProjectGanttProps = {
  projectId: string;
};

const DAY_WIDTH = 28;

function parseDuration(label: string): number {
  const match = label.match(/duration:\s*(\d+)\s*d/i);
  if (match) return Math.max(1, Number(match[1]));
  return label.toLowerCase().includes('milestone') ? 1 : 5;
}

function buildSchedule(
  nodes: Array<{ id: string; data: { label: string; kind: string } }>,
): GanttItem[] {
  const milestones = nodes.filter((n) => n.data.kind === 'Milestone');
  const tasks = nodes.filter((n) => n.data.kind === 'Task');
  const scheduleNodes = [...milestones, ...tasks];

  if (scheduleNodes.length === 0) {
    return nodes
      .filter((n) => ['Milestone', 'Task'].includes(n.data.kind))
      .map((node, index) => ({
        id: node.id,
        label: node.data.label,
        kind: node.data.kind as 'Milestone' | 'Task',
        startDay: index * 4,
        durationDays: parseDuration(node.data.label),
      }));
  }

  let cursor = 0;
  return scheduleNodes.map((node, index) => {
    const durationDays = parseDuration(node.data.label);
    const startDay = node.data.kind === 'Milestone' ? cursor : cursor + (index % 3);
    cursor += node.data.kind === 'Milestone' ? Math.max(durationDays, 3) : 0;
    return {
      id: node.id,
      label: node.data.label,
      kind: node.data.kind as 'Milestone' | 'Task',
      startDay,
      durationDays,
    };
  });
}

export default function ProjectGantt({ projectId }: ProjectGanttProps) {
  const [items, setItems] = useState<GanttItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const payload = await fetchReactFlow(projectId);
        const schedule = buildSchedule(payload.nodes);
        if (!cancelled) setItems(schedule);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load schedule');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const horizon = useMemo(() => {
    if (items.length === 0) return 30;
    return Math.max(
      30,
      ...items.map((item) => item.startDay + item.durationDays + 2),
    );
  }, [items]);

  if (loading) return <p className="text-slate-500">Loading Gantt…</p>;
  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-4 py-3">
        <h3 className="font-semibold text-slate-900">Schedule (Gantt)</h3>
        <p className="text-sm text-slate-500">
          Milestones and tasks from the project graph, laid out on a day timeline.
        </p>
      </div>

      {items.length === 0 ? (
        <div className="p-8 text-sm text-slate-500">
          No milestones or tasks yet. Create a project with an objective to invoke the
          schedule specialist.
        </div>
      ) : (
        <div className="overflow-x-auto p-4">
          <div className="min-w-[720px]">
            <div
              className="mb-3 grid text-[10px] uppercase tracking-wide text-slate-400"
              style={{ gridTemplateColumns: `220px repeat(${horizon}, ${DAY_WIDTH}px)` }}
            >
              <div />
              {Array.from({ length: horizon }, (_, day) => (
                <div key={day} className="text-center">
                  {day % 7 === 0 ? `D${day}` : ''}
                </div>
              ))}
            </div>

            {items.map((item) => (
              <div
                key={item.id}
                className="mb-2 grid items-center"
                style={{ gridTemplateColumns: `220px repeat(${horizon}, ${DAY_WIDTH}px)` }}
              >
                <div className="truncate pr-3 text-sm text-slate-700" title={item.label}>
                  <span
                    className={`mr-2 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                      item.kind === 'Milestone'
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-brand-100 text-brand-800'
                    }`}
                  >
                    {item.kind}
                  </span>
                  {item.label.replace(/^(Milestone|Task):\s*/i, '')}
                </div>
                {Array.from({ length: horizon }, (_, day) => {
                  const active = day >= item.startDay && day < item.startDay + item.durationDays;
                  return (
                    <div key={day} className="h-8 border border-slate-100 bg-slate-50">
                      {active && day === item.startDay && (
                        <div
                          className={`h-full rounded-sm ${
                            item.kind === 'Milestone' ? 'bg-amber-400' : 'bg-brand-500'
                          }`}
                          style={{
                            width: `${item.durationDays * DAY_WIDTH - 4}px`,
                          }}
                          title={item.label}
                        />
                      )}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
