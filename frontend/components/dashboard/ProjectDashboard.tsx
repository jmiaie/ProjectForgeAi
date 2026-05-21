'use client';

import { useState } from 'react';

import ProjectChat from '@/components/chat/ProjectChat';
import ProjectOverview from '@/components/dashboard/ProjectOverview';
import ProjectGantt from '@/components/gantt/ProjectGantt';
import ProjectGraphView from '@/components/graph/ProjectGraphView';

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'graph', label: 'Graph' },
  { id: 'gantt', label: 'Gantt' },
  { id: 'chat', label: 'Chat' },
] as const;

type TabId = (typeof TABS)[number]['id'];

type ProjectDashboardProps = {
  projectId: string;
};

export default function ProjectDashboard({ projectId }: ProjectDashboardProps) {
  const [tab, setTab] = useState<TabId>('overview');

  return (
    <div>
      <div className="mb-6 flex flex-wrap gap-2">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={`rounded-md px-4 py-2 text-sm font-medium ${
              tab === item.id
                ? 'bg-brand-600 text-white'
                : 'bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === 'overview' && <ProjectOverview projectId={projectId} />}
      {tab === 'graph' && <ProjectGraphView projectId={projectId} />}
      {tab === 'gantt' && <ProjectGantt projectId={projectId} />}
      {tab === 'chat' && <ProjectChat projectId={projectId} />}
    </div>
  );
}
