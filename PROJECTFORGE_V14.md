# ProjectForge AI — Master Build Framework v14

**Universal Agentic Project Management OS in a Box**

Copy this entire markdown and paste it into Claude, Cursor, Lovable, Manus, or any other coding AI. This is the parallel-development source of truth for the v14 starter.

## 1. Project Vision & Principles

**Name:** ProjectForge AI

**Tagline:** Upload all project documents once -> instant living project graph -> auto-generates every template, contract, schedule, automation, communication loop, and compliance control.

**Scope:** Industry-agnostic. Construction is the anchor workflow, but the framework supports software, consulting, healthcare builds, legal, events, M&A, and short-form gigs.

**Core promise:** PM framework in a box with accuracy grounding via custom protocols, Locus, and persistent memory.

**Universal accessibility:** Solopreneurs on free/low-cost tiers through enterprises with RBAC, audit, and on-prem/air-gapped deployment.

**LLM strategy:** Low-cost models by default, flagship upsells, and bring-your-own keys across providers.

**Integrations:** One Intake Wizard for OAuth 2.0/PKCE, API keys, webhooks, and MCP servers.

**Compliance-first:** HIPAA priority plus modular SOC 2, GDPR, and legal controls. Self-learning/healing is gated by project category.

**Data-first:** Phase 1 supports PDFs, images, emails, and Office files. Later phases add CAD/BIM, codebases, databases, and specialized sources.

## 2. High-Level Architecture

```text
User Upload + Intake Wizard (OAuth / API / MCP)
    ↓
Ingestion Pipeline (parsers -> Locus.index + OMPA.record)
    ↓
HybridStore (Locus + OMPA Vault + Neo4j Project Graph)
    ↓
Integrations Manager (MCP tool discovery)
    ↓
Orchestrator Agent (LangGraph) + Specialist Agents
    ↓
LLM Router (LiteLLM - low-cost default + flagship/BYO)
    ↓
ComplianceEnforcer + SelfImprover (gated) + UpgradeManager
    ↓
Temporal Workflows (timed emails, recurring reports, automations)
    ↓
Frontend Dashboard (React Flow, chat, templates, Gantt)
```

Per-project isolation: dedicated Locus store, OMPA vault, encrypted blobs, and graph partitioning.

## 3. Tech Stack

- **Backend:** FastAPI + LangGraph + Temporal.io (Python)
- **LLM layer:** LiteLLM for 100+ providers and local Ollama
- **Storage:** Locus + OMPA + optional RTK + Neo4j + PostgreSQL
- **Integrations:** Authlib OAuth + MCP Python SDK
- **Frontend:** Next.js 15 + TypeScript + shadcn/ui + React Flow + Tailwind
- **Deployment:** SaaS default with hybrid/on-prem manifests

## 4. Repository Structure

```text
projectforge-ai/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   └── orchestrator.py
│   │   ├── compliance/
│   │   │   └── enforcer.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── integrations_manager.py
│   │   │   └── llm_router.py
│   │   ├── ingestion/
│   │   │   ├── pipeline.py
│   │   │   └── parsers/common/
│   │   ├── integrations/
│   │   │   ├── registry.py
│   │   │   ├── intake_form.py
│   │   │   └── connectors/
│   │   │       ├── mcp.py
│   │   │       └── oauth.py
│   │   ├── storage/
│   │   │   ├── locus_adapter.py
│   │   │   ├── ompa_adapter.py
│   │   │   └── rtk_adapter.py
│   │   └── main.py
├── frontend/
│   ├── app/settings/connections/page.tsx
│   └── components/IntakeWizard.tsx
├── submodules/
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## 5. Core Code Files

### `backend/app/core/config.py`

```python
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "ProjectForge AI"
    DEPLOYMENT_MODE: Literal["saas", "hybrid", "onprem"] = "saas"
    DEFAULT_COMPLIANCE: str = "standard"
    DEFAULT_LLM_MODEL: str = "groq/llama-3.1-70b-versatile"
    NEO4J_URI: str = "bolt://neo4j:7687"
    POSTGRES_URI: str = "postgresql://projectforge:projectforge@postgres:5432/projectforge"
    ENCRYPTION_KEY: str = "dev-only-change-me"
    LOCUS_SOURCE_PATH: str | None = None
    LOCUS_ENGINE: str = "locus:LocusEngine"
    LOCUS_STORE_ROOT: str = "./.locus"
    OMPA_SOURCE_PATH: str | None = None
    OMPA_ENGINE: str = "ompa:Ompa"
    OMPA_VAULT_ROOT: str = "./vaults"
    REQUIRE_NATIVE_LOCUS_OMPA: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
```

### `backend/app/compliance/enforcer.py`

```python
from dataclasses import dataclass

from core.config import settings


@dataclass(frozen=True)
class ComplianceProfile:
    project_id: str
    category: str
    allow_self_learning: bool = True


def get_compliance_profile(project_id: str) -> ComplianceProfile:
    category = settings.DEFAULT_COMPLIANCE.lower()
    restricted = category in {"hipaa", "legal"}
    return ComplianceProfile(project_id=project_id, category=category, allow_self_learning=not restricted)
```

### `backend/app/core/llm_router.py`

```python
from typing import Any

from pydantic import BaseModel

from compliance.enforcer import get_compliance_profile
from core.config import settings


class LLMRequest(BaseModel):
    messages: list[dict[str, Any]]
    project_id: str
    model: str | None = None
    task_type: str = "general"


class LLMRouter:
    async def call(self, req: LLMRequest) -> str:
        profile = get_compliance_profile(req.project_id)
        if profile.category in {"hipaa", "legal"}:
            model = "anthropic/claude-3-5-sonnet-20241022"
        else:
            model = req.model or settings.DEFAULT_LLM_MODEL

        import litellm

        response = await litellm.acompletion(
            model=model,
            messages=req.messages,
            temperature=0.3 if req.task_type == "reasoning" else 0.0,
        )
        return response.choices[0].message.content
```

### `backend/app/core/integrations_manager.py`

```python
from integrations.registry import ConnectorRegistry


class IntegrationsManager:
    async def get_recommended_connectors(self, project_id: str | None = None, compliance: str = "standard") -> list[str]:
        return ConnectorRegistry.get_recommended(compliance)

    async def connect(self, connector_type: str, auth_data: dict, project_id: str | None = None) -> dict:
        connector = ConnectorRegistry.get_connector(connector_type)
        connection = await connector.authenticate(auth_data)
        return {"status": "connected", "connector": connector_type, "project_id": project_id, "connection": connection}
```

### `backend/app/integrations/registry.py`

```python
from typing import Any


class ConnectorRegistry:
    _connectors: dict[str, dict[str, Any]] = {
        "google": {"type": "oauth", "provider": "google", "scopes": ["email", "calendar", "drive.readonly"]},
        "microsoft": {"type": "oauth", "provider": "microsoft", "mcp_support": True},
        "slack": {"type": "oauth"},
        "github": {"type": "oauth"},
        "jira": {"type": "api_key"},
        "mcp_server": {"type": "mcp", "description": "Any MCP server"},
    }

    @classmethod
    def get_connector(cls, name: str):
        config = cls._connectors.get(name)
        if config is None:
            raise ValueError(f"Unknown connector: {name}")
        if config["type"] == "oauth":
            from integrations.connectors.oauth import OAuthConnector
            return OAuthConnector(name, config)
        if config["type"] == "mcp":
            from integrations.connectors.mcp import MCPConnector
            return MCPConnector()
        if config["type"] == "api_key":
            from integrations.connectors.oauth import APIKeyConnector
            return APIKeyConnector(name, config)
        raise ValueError(f"Unsupported connector type: {config['type']}")

    @classmethod
    def get_recommended(cls, compliance: str = "standard") -> list[str]:
        if compliance.lower() == "hipaa":
            return ["microsoft", "mcp_server"]
        return list(cls._connectors.keys())
```

### `backend/app/integrations/intake_form.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.integrations_manager import IntegrationsManager


router = APIRouter(prefix="/intake", tags=["intake"])


class ConnectionRequest(BaseModel):
    connector_type: str = Field(..., examples=["google", "mcp_server"])
    auth_data: dict = Field(default_factory=dict)
    project_id: str | None = None


def get_integrations_manager() -> IntegrationsManager:
    return IntegrationsManager()


@router.get("/connections/recommended")
async def recommended_connections(compliance: str = "standard", manager: IntegrationsManager = Depends(get_integrations_manager)):
    connectors = await manager.get_recommended_connectors(compliance=compliance)
    return {"connectors": connectors}


@router.post("/connections")
async def run_intake(data: ConnectionRequest, manager: IntegrationsManager = Depends(get_integrations_manager)):
    try:
        return await manager.connect(data.connector_type, data.auth_data, data.project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
```

### `backend/app/main.py`

```python
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.config import settings
from core.integrations_manager import IntegrationsManager
from core.llm_router import LLMRouter
from ingestion.pipeline import IngestionPipeline
from integrations.intake_form import router as intake_router


app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(intake_router, prefix="/api/v1")


class CreateProjectRequest(BaseModel):
    files: list[str] = Field(default_factory=list)
    compliance: str = "standard"


def get_llm_router() -> LLMRouter:
    return LLMRouter()


def get_integrations_manager() -> IntegrationsManager:
    return IntegrationsManager()


def get_ingestion_pipeline() -> IngestionPipeline:
    return IngestionPipeline()


@app.post("/api/v1/projects/")
async def create_project(
    request: CreateProjectRequest,
    integrations_manager: IntegrationsManager = Depends(get_integrations_manager),
    ingestion: IngestionPipeline = Depends(get_ingestion_pipeline),
):
    project_id = "proj_123"
    await integrations_manager.get_recommended_connectors(compliance=request.compliance)
    ingestion_result = await ingestion.process_files(project_id, request.files)
    return {
        "project_id": project_id,
        "status": "orchestrated",
        "message": "ProjectForge AI is live!",
        "ingestion": ingestion_result,
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "llm_default": settings.DEFAULT_LLM_MODEL}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### `frontend/components/IntakeWizard.tsx`

```tsx
'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

type IntakeWizardProps = {
  onComplete?: () => void;
};

export default function IntakeWizard({ onComplete }: IntakeWizardProps) {
  const [recommended, setRecommended] = useState<string[]>(['google', 'microsoft', 'slack', 'github', 'mcp_server']);
  const [status, setStatus] = useState<string>('');

  useEffect(() => {
    fetch('/api/v1/intake/connections/recommended')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.connectors) setRecommended(data.connectors);
      })
      .catch(() => {});
  }, []);

  const handleConnect = async (type: string) => {
    setStatus(`Connecting to ${type}...`);
    const payload = type === 'mcp_server' ? { server_url: 'https://example-mcp.local' } : { code: 'placeholder-oauth-code' };
    const response = await fetch('/api/v1/intake/connections', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ connector_type: type, auth_data: payload }),
    });
    setStatus(response.ok ? `${type} connected` : `${type} needs configuration`);
  };

  return (
    <Card className="mx-auto max-w-2xl p-8">
      <h1 className="mb-2 text-3xl font-bold">Connect Your Tools</h1>
      <p className="mb-8 text-sm text-muted-foreground">
        ProjectForge can ingest calendars, files, chat, issue trackers, and MCP tools.
      </p>
      <div className="grid grid-cols-2 gap-4">
        {recommended.map((tool) => (
          <Button key={tool} variant="outline" className="h-24 flex-col" onClick={() => handleConnect(tool)}>
            <span className="text-lg capitalize">{tool.replace('_', ' ')}</span>
          </Button>
        ))}
      </div>
      {status ? <p className="mt-4 text-sm">{status}</p> : null}
      <Button onClick={onComplete} className="mt-8 w-full">Skip & Continue</Button>
    </Card>
  );
}
```

## 6. Local Run

```bash
cp .env.example .env
docker-compose up backend
curl http://localhost:8000/health
```

### Native Locus + OMPA

Use installed packages or point ProjectForge at local source checkouts:

```env
LOCUS_SOURCE_PATH=/absolute/path/to/locus
LOCUS_ENGINE=locus:LocusEngine
LOCUS_STORE_ROOT=./.locus
OMPA_SOURCE_PATH=/absolute/path/to/ompa
OMPA_ENGINE=ompa:Ompa
OMPA_VAULT_ROOT=./vaults
REQUIRE_NATIVE_LOCUS_OMPA=true
```

`/health` and `/api/v1/storage/{project_id}/status` expose whether native Locus/OMPA are loaded.

Direct Python:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=backend/app uvicorn main:app --reload
```

## 7. Parallel Development Instructions

- **Cursor:** Final integration, local running, git, PRs.
- **Claude:** Deep agent logic, LangGraph orchestration, specialist-agent behavior.
- **Grok:** Master framework coordination and product framing.
- **Lovable:** Full-stack UI generation, dashboard, flows, templates.
- **Manus:** Autonomous tests for OAuth, MCP, ingestion, and end-to-end smoke scripts.

## 8. Next File to Generate

Build the Phase 1 PDF ingestion parser:

```text
backend/app/ingestion/parsers/common/pdf.py
```

It should extract text, page metadata, tables where possible, source hashes, and confidence warnings, then produce chunks ready for `LocusAdapter.index_files()` and OMPA decision records.
