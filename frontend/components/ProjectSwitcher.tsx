'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

type ProjectListItem = {
  project_id: string;
  name: string;
  status: string;
};

type ProjectSwitcherProps = {
  activeProjectId: string;
};

export function ProjectSwitcher({ activeProjectId }: ProjectSwitcherProps) {
  const [projects, setProjects] = useState<ProjectListItem[]>([]);

  useEffect(() => {
    fetch('/api/v1/projects')
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (data?.projects) {
          setProjects(data.projects);
        }
      })
      .catch(() => setProjects([]));
  }, [activeProjectId]);

  const active = projects.find((project) => project.project_id === activeProjectId);

  return (
    <div className="row" style={{ gap: '0.75rem', alignItems: 'center' }}>
      <label className="muted" htmlFor="project-switcher">
        Project
      </label>
      <select
        id="project-switcher"
        className="input"
        value={activeProjectId}
        onChange={(event) => {
          window.location.href = `/?projectId=${encodeURIComponent(event.target.value)}`;
        }}
      >
        {projects.length ? (
          projects.map((project) => (
            <option key={project.project_id} value={project.project_id}>
              {project.name} ({project.project_id})
            </option>
          ))
        ) : (
          <option value={activeProjectId}>{activeProjectId}</option>
        )}
      </select>
      {active ? <span className="muted">{active.status}</span> : null}
      <Link href="/portfolio" className="muted">
        Portfolio
      </Link>
    </div>
  );
}
