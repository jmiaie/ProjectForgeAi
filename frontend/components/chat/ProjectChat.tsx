'use client';

import { useState } from 'react';

import { orchestrate, retrieveMemory } from '@/lib/api';

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
};

type ProjectChatProps = {
  projectId: string;
};

export default function ProjectChat({ projectId }: ProjectChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        'Ask anything about this project. I search indexed documents via Locus and can run the orchestrator for multi-step planning.',
    },
  ]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);

  async function handleSend(event: React.FormEvent) {
    event.preventDefault();
    const query = input.trim();
    if (!query || busy) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setBusy(true);

    try {
      const retrieval = await retrieveMemory(projectId, query);
      const snippets = retrieval.results
        .map((result, index) => {
          const text = result.text?.trim() || '(empty chunk)';
          const source = result.source ? ` · ${result.source}` : '';
          return `${index + 1}. ${text.slice(0, 400)}${source}`;
        })
        .join('\n\n');

      const assistantText =
        retrieval.result_count > 0
          ? `Found ${retrieval.result_count} relevant chunk(s):\n\n${snippets}`
          : 'No indexed chunks matched that query yet. Try uploading more documents or broadening the question.';

      setMessages((prev) => [
        ...prev,
        { id: `assistant-${Date.now()}`, role: 'assistant', content: assistantText },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: err instanceof Error ? err.message : 'Retrieval failed',
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  async function handleOrchestrate() {
    const objective =
      input.trim() ||
      'Summarize project status and recommend next actions based on indexed context.';
    setBusy(true);
    setMessages((prev) => [
      ...prev,
      { id: `user-orch-${Date.now()}`, role: 'user', content: `Orchestrate: ${objective}` },
    ]);
    try {
      const result = await orchestrate(projectId, objective);
      const summary =
        result.final_summary ||
        `Orchestration complete. Specialists: ${(result.specialists_invoked ?? []).join(', ') || 'none'}.`;
      setMessages((prev) => [
        ...prev,
        { id: `assistant-orch-${Date.now()}`, role: 'assistant', content: summary },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: `error-orch-${Date.now()}`,
          role: 'assistant',
          content: err instanceof Error ? err.message : 'Orchestration failed',
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-[620px] flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-4 py-3">
        <h3 className="font-semibold text-slate-900">Project chat</h3>
        <p className="text-sm text-slate-500">Grounded retrieval over Locus + optional orchestrator runs.</p>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`max-w-[90%] rounded-lg px-4 py-3 text-sm whitespace-pre-wrap ${
              message.role === 'user'
                ? 'ml-auto bg-brand-600 text-white'
                : 'bg-slate-100 text-slate-800'
            }`}
          >
            {message.content}
          </div>
        ))}
      </div>

      <form onSubmit={handleSend} className="border-t border-slate-200 p-4">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          rows={3}
          placeholder="Ask about contracts, schedule, risks, or uploaded documents…"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <div className="mt-3 flex gap-2">
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {busy ? 'Working…' : 'Ask Locus'}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={handleOrchestrate}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
          >
            Run orchestrator
          </button>
        </div>
      </form>
    </div>
  );
}
