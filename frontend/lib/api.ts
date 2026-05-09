export type HealthResponse = {
  status: string;
  llm_default: string;
  storage: Record<string, unknown>;
};

export type GraphStatus = {
  project_id: string;
  built: boolean;
  node_count: number;
  edge_count: number;
  storage: Record<string, unknown>;
};

export type ComplianceProfile = {
  project_id: string;
  category: string;
  allow_memory_writes: boolean;
  allow_self_learning: boolean;
  require_human_approval_for_external_writes: boolean;
  redact_before_llm: boolean;
};

export type ConnectionRecord = {
  connector_type: string;
  status: string;
  summary: Record<string, unknown>;
};

export type OrchestratorRun = {
  run_id: string;
  project_id: string;
  status: string;
  steps: Array<{ name: string; status: string; summary: string; output: Record<string, unknown> }>;
  artifacts: Record<string, unknown>;
  warnings: string[];
};

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(path, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`${path} failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`${path} failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function defaultProjectId(): string {
  return process.env.NEXT_PUBLIC_DEFAULT_PROJECT_ID || 'proj_123';
}
