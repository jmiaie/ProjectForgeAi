'use client';

import { useState } from 'react';

import { createProject } from '@/lib/api';
import { useAuth } from '@/lib/auth';

type CreateProjectFormProps = {
  onCreated?: (projectId: string) => void;
};

export default function CreateProjectForm({ onCreated }: CreateProjectFormProps) {
  const { token } = useAuth();
  const [name, setName] = useState('');
  const [objective, setObjective] = useState('');
  const [compliance, setCompliance] = useState('standard');
  const [files, setFiles] = useState<FileList | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const form = new FormData();
      if (name) form.append('name', name);
      if (objective) form.append('objective', objective);
      form.append('compliance', compliance);
      if (files) {
        Array.from(files).forEach((file) => form.append('files', file));
      }
      const payload = await createProject(form, token);
      setResult(payload.project_id);
      onCreated?.(payload.project_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
    >
      <h2 className="text-xl font-semibold text-slate-900">Create project</h2>
      <p className="mt-1 text-sm text-slate-600">
        Upload documents, CAD/BIM files, or repo archives to seed the living graph.
      </p>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <label className="block text-sm">
          <span className="font-medium text-slate-700">Name</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            placeholder="Riverside Tower"
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium text-slate-700">Compliance</span>
          <select
            value={compliance}
            onChange={(e) => setCompliance(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
          >
            <option value="standard">Standard</option>
            <option value="hipaa">HIPAA</option>
            <option value="soc2">SOC 2</option>
            <option value="gdpr">GDPR</option>
          </select>
        </label>
      </div>

      <label className="mt-4 block text-sm">
        <span className="font-medium text-slate-700">Objective</span>
        <textarea
          value={objective}
          onChange={(e) => setObjective(e.target.value)}
          rows={3}
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
          placeholder="Generate schedule, contracts, and compliance controls for kickoff."
        />
      </label>

      <label className="mt-4 block text-sm">
        <span className="font-medium text-slate-700">Files</span>
        <input
          type="file"
          multiple
          onChange={(e) => setFiles(e.target.files)}
          className="mt-1 block w-full text-sm text-slate-600"
        />
      </label>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      {result && (
        <p className="mt-3 text-sm text-emerald-700">
          Project created: <span className="font-mono">{result}</span>
        </p>
      )}

      <button
        type="submit"
        disabled={busy}
        className="mt-5 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
      >
        {busy ? 'Creating…' : 'Create & ingest'}
      </button>
    </form>
  );
}
