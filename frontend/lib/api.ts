export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export type Project = {
  id: string;
  name: string;
  compliance: string;
  status: string;
  objective?: string | null;
  organization_id?: string | null;
  created_at?: string;
};

export type GraphStats = {
  project_id: string;
  total_nodes: number;
  total_edges: number;
  nodes_by_kind: Record<string, number>;
  edges_by_kind: Record<string, number>;
};

export type ReactFlowPayload = {
  nodes: Array<{
    id: string;
    type?: string;
    position: { x: number; y: number };
    data: { label: string; kind: string; properties?: Record<string, unknown> };
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    label?: string;
    animated?: boolean;
    data?: Record<string, unknown>;
  }>;
};

export type MemoryStats = {
  project_id: string;
  locus: Record<string, unknown>;
  ompa: Record<string, unknown>;
};

export type RetrieveResult = {
  project_id: string;
  query: string;
  results: Array<{
    text?: string;
    source?: string;
    score?: number;
    metadata?: Record<string, unknown>;
  }>;
  result_count: number;
};

export type User = {
  id: string;
  email: string;
  full_name?: string | null;
  is_superuser?: boolean;
};

function authHeaders(token?: string | null): HeadersInit {
  const headers: Record<string, string> = {
    Accept: 'application/json',
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    const detail = payload.detail ?? payload.message ?? res.statusText;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export async function login(email: string, password: string) {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  return parseJson<{ access_token: string; user: User }>(res);
}

export async function register(email: string, password: string, fullName?: string) {
  const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
  return parseJson<{ access_token: string; user: User }>(res);
}

export async function fetchMe(token: string) {
  const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
    headers: authHeaders(token),
  });
  return parseJson<User>(res);
}

export async function listProjects(token?: string | null) {
  const res = await fetch(`${API_BASE}/api/v1/projects/`, {
    headers: authHeaders(token),
  });
  return parseJson<{ items: Project[] }>(res);
}

export async function fetchProject(projectId: string, token?: string | null) {
  const res = await fetch(`${API_BASE}/api/v1/projects/${projectId}`, {
    headers: authHeaders(token),
  });
  return parseJson<Project>(res);
}

export async function createProject(
  form: FormData,
  token?: string | null,
) {
  const res = await fetch(`${API_BASE}/api/v1/projects/`, {
    method: 'POST',
    headers: token ? authHeaders(token) : {},
    body: form,
  });
  return parseJson<{
    project_id: string;
    status: string;
    ingestion: Record<string, unknown>;
    plan: Record<string, unknown> | null;
  }>(res);
}

export async function fetchGraphStats(projectId: string) {
  const res = await fetch(`${API_BASE}/api/v1/projects/${projectId}/graph/stats`);
  return parseJson<GraphStats>(res);
}

export async function fetchReactFlow(projectId: string) {
  const res = await fetch(`${API_BASE}/api/v1/projects/${projectId}/graph/react-flow`);
  return parseJson<ReactFlowPayload>(res);
}

export async function fetchMemoryStats(projectId: string) {
  const res = await fetch(`${API_BASE}/api/v1/projects/${projectId}/memory/stats`);
  return parseJson<MemoryStats>(res);
}

export async function retrieveMemory(projectId: string, query: string, limit = 8) {
  const res = await fetch(`${API_BASE}/api/v1/projects/${projectId}/memory/retrieve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, limit }),
  });
  return parseJson<RetrieveResult>(res);
}

export async function orchestrate(projectId: string, objective: string) {
  const res = await fetch(`${API_BASE}/api/v1/agents/orchestrate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId, objective }),
  });
  return parseJson<{
    final_summary?: string;
    specialists_invoked?: string[];
    plan?: unknown[];
    warnings?: string[];
  }>(res);
}
