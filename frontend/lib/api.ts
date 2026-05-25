export type HealthResponse = {
  status: string;
  llm_default: string;
  deployment_mode?: string;
  project_tier?: string;
  rbac_enforce?: boolean;
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
  goal: string;
  status: string;
  steps: Array<{ name: string; status: string; summary: string; output: Record<string, unknown> }>;
  artifacts: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  warnings: string[];
};

export type OrchestratorAuditEvent = {
  id: string;
  event_type: string;
  message: string;
  run_id: string;
  created_at: string;
  metadata?: Record<string, unknown>;
};

export type UpgradeStatus = {
  project_id: string;
  project_tier: string;
  deployment_mode: string;
  compliance_category: string;
  allow_self_learning: boolean;
  features: Record<string, { enabled: boolean; required_tier: string; description: string }>;
};

export type AutomationRecord = {
  id: string;
  project_id: string;
  type: string;
  name: string;
  status: string;
  run_count: number;
  next_run_at?: string | null;
  schedule?: {
    interval_seconds?: number | null;
    run_at?: string | null;
    cron?: string | null;
  };
};

function actorHeaders(extra: HeadersInit = {}): HeadersInit {
  const headers = new Headers(extra);
  const actor = process.env.NEXT_PUBLIC_RBAC_ACTOR;
  const role = process.env.NEXT_PUBLIC_RBAC_ROLE;
  if (typeof window !== 'undefined') {
    const token = window.localStorage.getItem('projectforge_auth_token');
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
  }
  if (actor) {
    headers.set('X-ProjectForge-Actor', actor);
  }
  if (role) {
    headers.set('X-ProjectForge-Role', role);
  }
  return headers;
}

export function setAuthToken(token: string | null) {
  if (typeof window === 'undefined') {
    return;
  }
  if (token) {
    window.localStorage.setItem('projectforge_auth_token', token);
  } else {
    window.localStorage.removeItem('projectforge_auth_token');
  }
}

export type AuthStatus = {
  enabled: boolean;
  mock_mode: boolean;
  issuer?: string | null;
  configured: boolean;
  active_sessions: number;
};

export type AuthSession = {
  token: string;
  actor_id: string;
  email?: string | null;
  role: string;
  groups: string[];
  provider?: string;
  expires_at?: string;
};

export type SOC2Export = {
  project_id: string;
  framework: string;
  generated_at: string;
  summary: {
    control_count: number;
    implemented: number;
    partial: number;
  };
  controls: Array<{
    control_id: string;
    title: string;
    status: string;
  }>;
};

export type ExecutiveDashboard = {
  generated_at: string;
  widgets: {
    portfolio_health: {
      active_projects: number;
      graphs_built: number;
      total_nodes: number;
      total_edges: number;
    };
    compliance_posture: {
      by_category: Record<string, number>;
      restricted_profiles: number;
      denied_actions: number;
      projects_with_gaps: number;
    };
    risk_summary: {
      total_risks: number;
      by_severity: Record<string, number>;
      high_risk_projects: number;
      top_projects: Array<{ project_id: string; name: string; risk_count: number }>;
    };
  };
};

export type PortfolioOrchestratorRun = {
  portfolio_run_id: string;
  goal: string;
  status: string;
  project_runs: Array<{ project_id: string; run_id: string; status: string; summary: string }>;
  artifacts: Record<string, unknown>;
};

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(path, { cache: 'no-store', headers: actorHeaders() });
  if (!response.ok) {
    throw new Error(`${path} failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(path, {
    method: 'POST',
    headers: actorHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`${path} failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(path, {
    method: 'PATCH',
    headers: actorHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`${path} failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function apiDelete<T>(path: string): Promise<T> {
  const response = await fetch(path, { method: 'DELETE', headers: actorHeaders() });
  if (!response.ok) {
    throw new Error(`${path} failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function defaultProjectId(): string {
  return process.env.NEXT_PUBLIC_DEFAULT_PROJECT_ID || 'proj_123';
}
