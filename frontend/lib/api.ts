const DEFAULT_API = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export function getApiBase(): string {
  return DEFAULT_API.replace(/\/$/, '');
}

export function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('pf_token');
}

export function setAuthToken(token: string): void {
  localStorage.setItem('pf_token', token);
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getAuthToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (!headers.has('Content-Type') && init.body && typeof init.body === 'string') {
    headers.set('Content-Type', 'application/json');
  }
  const res = await fetch(`${getApiBase()}${path}`, { ...init, headers });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export type ProjectSummary = {
  id: string;
  name: string;
  status: string;
  compliance: string;
};

export type ReactFlowPayload = {
  nodes: Array<{
    id: string;
    position: { x: number; y: number };
    data: { label: string; kind: string };
  }>;
  edges: Array<{ id: string; source: string; target: string; label?: string }>;
};
