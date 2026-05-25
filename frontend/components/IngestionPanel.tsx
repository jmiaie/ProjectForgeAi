'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { apiPost } from '@/lib/api';

type IngestionPanelProps = {
  projectId: string;
};

export function IngestionPanel({ projectId }: IngestionPanelProps) {
  const [files, setFiles] = useState<FileList | null>(null);
  const [schema, setSchema] = useState('public');
  const [result, setResult] = useState<Record<string, unknown> | undefined>();
  const [error, setError] = useState('');

  const upload = async () => {
    if (!files?.length) {
      setError('Choose at least one project document first.');
      return;
    }
    setError('');
    const form = new FormData();
    form.set('project_id', projectId);
    form.set('compliance', 'standard');
    Array.from(files).forEach((file) => form.append('files', file));
    const response = await fetch('/api/v1/projects/upload', {
      method: 'POST',
      body: form,
    });
    if (!response.ok) {
      setError(`Upload failed with ${response.status}`);
      return;
    }
    setResult(await response.json());
  };

  const snapshotDatabase = async () => {
    setError('');
    try {
      const payload = await apiPost<Record<string, unknown>>(
        `/api/v1/projects/${projectId}/ingestion/database-snapshot`,
        { db_schema: schema },
      );
      setResult(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Database snapshot failed');
    }
  };

  return (
    <Card className="panel">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Source of Truth</div>
          <h2>Document ingestion</h2>
          <p className="muted">
            Upload PDFs, emails, Office files, images, IFC/DWG, codebase archives (.zip), or PostgreSQL schema snapshots.
          </p>
        </div>
        <Button onClick={upload}>Upload</Button>
      </div>
      <div className="stack">
        <input
          className="input"
          type="file"
          multiple
          accept=".pdf,.eml,.mbox,.docx,.xlsx,.pptx,.png,.jpg,.jpeg,.ifc,.dwg,.zip,.tar,.tar.gz,.tgz"
          onChange={(event) => setFiles(event.target.files)}
        />
        <div className="button-row">
          <input
            className="input"
            value={schema}
            onChange={(event) => setSchema(event.target.value)}
            aria-label="Database schema"
            placeholder="public"
          />
          <Button variant="outline" onClick={snapshotDatabase}>
            PostgreSQL schema snapshot
          </Button>
        </div>
        {error ? <p className="badge badge-warning">{error}</p> : null}
        {result ? <pre className="code">{JSON.stringify(result, null, 2)}</pre> : null}
      </div>
    </Card>
  );
}
