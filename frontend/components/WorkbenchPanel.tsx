'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { apiPost } from '@/lib/api';

type WorkbenchResponse = {
  answer: string;
  context: Array<{ source: string; text: string }>;
  graph: { sources: string[]; node_count: number };
};

type WorkbenchPanelProps = {
  projectId: string;
};

export function WorkbenchPanel({ projectId }: WorkbenchPanelProps) {
  const [query, setQuery] = useState('What are the key project sources?');
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState<string[]>([]);
  const [contextCount, setContextCount] = useState(0);
  const [message, setMessage] = useState('');

  const runQuery = async () => {
    setMessage('Retrieving grounded context...');
    try {
      const result = await apiPost<WorkbenchResponse>(
        `/api/v1/projects/${projectId}/workbench/query`,
        { query, limit: 5 },
      );
      setAnswer(result.answer);
      setSources(result.graph.sources);
      setContextCount(result.context.length);
      setMessage(`Grounded with ${result.context.length} context item(s).`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Workbench query failed.');
    }
  };

  return (
    <Card className="panel">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Workbench</div>
          <h2>Grounded chat</h2>
          <p className="muted">Query Locus context with graph source awareness.</p>
        </div>
        <Button onClick={runQuery}>Ask</Button>
      </div>
      <textarea
        className="textarea"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        rows={3}
      />
      {answer ? <p>{answer}</p> : null}
      {sources.length ? (
        <div className="chip-row">
          {sources.map((source) => (
            <span key={source} className="chip">
              {source}
            </span>
          ))}
        </div>
      ) : null}
      <p className="muted">
        {message || `Context items: ${contextCount}. Graph-backed sources: ${sources.length}.`}
      </p>
    </Card>
  );
}
