'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

type IngestionPanelProps = {
  projectId: string;
};

export function IngestionPanel({ projectId }: IngestionPanelProps) {
  const [files, setFiles] = useState<FileList | null>(null);
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

  return (
    <Card className="panel">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Source of Truth</div>
          <h2>Document ingestion</h2>
          <p className="muted">Upload PDFs, emails, Office files, or images to build manifests and graphs.</p>
        </div>
        <Button onClick={upload}>Upload</Button>
      </div>
      <div className="stack">
        <input className="input" type="file" multiple onChange={(event) => setFiles(event.target.files)} />
        {error ? <p className="badge badge-warning">{error}</p> : null}
        {result ? <pre className="code">{JSON.stringify(result, null, 2)}</pre> : null}
      </div>
    </Card>
  );
}
