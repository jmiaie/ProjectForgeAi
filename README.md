# ProjectForge AI — Master Build Framework v14

**Universal Agentic Project Management OS in a Box**

Copy this markdown into Claude, Cursor, Lovable, Manus, or other coding agents as the single source of truth for parallel development.

## 1. Project Vision & Principles

- **Name:** ProjectForge AI
- **Tagline:** Upload all project documents once -> instant living project graph -> auto-generates templates, contracts, schedules, automations, communications, and compliance controls.
- **Scope:** Industry-agnostic, with construction as the anchor use case and support for software, consulting, healthcare builds, legal, events, M&A, and small gigs.
- **Core promise:** PM framework in a box with accuracy grounding through custom protocols and Locus.
- **Accessibility:** Solopreneurs on a free/low-cost tier through enterprises with RBAC, audit, and on-prem support.
- **LLM strategy:** Low-cost efficient models by default, flagship upsell, and bring-your-own API keys for any provider.
- **Integrations:** Extensible Intake Wizard supporting OAuth 2.0/PKCE, API keys, webhooks, and MCP.
- **Compliance-first:** HIPAA priority plus modular SOC 2, GDPR, and legal controls. Self-learning is gated by project category.
- **Data-first:** Phase 1 supports PDFs, images, emails, and Office files. Later phases adapt to CAD/BIM, codebases, databases, and more.

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

Per-project isolation uses a dedicated Locus store, OMPA vault, and encrypted blobs.

## 3. Tech Stack

- **Backend:** FastAPI + LangGraph + Temporal.io (Python)
- **LLM layer:** LiteLLM for 100+ providers and local Ollama
- **Storage:** Locus, OMPA, optional RTK, Neo4j, PostgreSQL
- **Integrations:** Authlib OAuth + MCP Python SDK
- **Frontend:** Next.js 15 + TypeScript + shadcn/ui + React Flow + Tailwind
- **Deployment:** Hybrid-first SaaS default with on-prem/air-gapped manifests

## 4. Repository Structure

```text
projectforge-ai/
├── backend/
│   └── app/
│       ├── agents/
│       ├── compliance/
│       ├── core/
│       ├── ingestion/
│       │   └── parsers/common/
│       ├── integrations/
│       │   └── connectors/
│       ├── storage/
│       └── main.py
├── frontend/
│   ├── app/settings/connections/page.tsx
│   └── components/IntakeWizard.tsx
├── submodules/
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## 5. Local Run

```bash
cp .env.example .env
docker-compose up backend frontend
curl http://localhost:8000/health
```

### Native Locus + OMPA Integration

ProjectForge loads your native Locus and OMPA implementations directly. Install them as Python packages or point the app at local checkouts:

```env
LOCUS_SOURCE_PATH=/absolute/path/to/locus
LOCUS_ENGINE=locus:LocusEngine
LOCUS_STORE_ROOT=./.locus
OMPA_SOURCE_PATH=/absolute/path/to/ompa
OMPA_ENGINE=ompa:Ompa
OMPA_VAULT_ROOT=./vaults
REQUIRE_NATIVE_LOCUS_OMPA=true
```

`/health` and `/api/v1/storage/{project_id}/status` report whether native Locus/OMPA are loaded or the development fallback is active.

### Phase 1 Ingestion

Current ingestion supports:

- PDF text extraction via `pypdf`
- Email `.eml` body/header extraction
- Office Open XML starters for DOCX, XLSX, and PPTX
- Image metadata stubs with explicit OCR-not-configured warnings
- Multipart upload endpoint: `POST /api/v1/projects/upload`
- Per-project ingestion manifest at `INGESTION_MANIFEST_ROOT/{project_id}/latest.json`

### Project Graph Builder

Ingestion manifests now build starter project graphs with provenance:

- Project, document, and chunk nodes
- `HAS_DOCUMENT` and `HAS_CHUNK` edges
- Source hash and parser metadata on graph nodes
- Neo4j adapter with in-memory fallback for local development
- Graph endpoints:
  - `POST /api/v1/projects/{project_id}/graph/build`
  - `GET /api/v1/projects/{project_id}/graph`
  - `GET /api/v1/projects/{project_id}/graph/status`

### Orchestrator Agent

The starter orchestrator runs deterministic specialist steps over the graph/Locus/OMPA tool context:

- Intake analyst
- Scheduler
- Risk analyst
- Compliance reviewer
- Template generator

Endpoints:

- `POST /api/v1/orchestrator/run`
- `GET /api/v1/projects/{project_id}/orchestrator/status`

### Compliance Enforcement

Compliance profiles now gate sensitive actions and produce audit events:

- Profiles: `standard`, `hipaa`, `legal`, `soc2`, `gdpr`
- Redaction hooks for email, phone, SSN, MRN, and DOB patterns before restricted LLM calls
- Memory-write gating for HIPAA/legal/GDPR profiles
- External-write approval gating for restricted integrations
- Audit event stream per project

Endpoints:

- `GET /api/v1/projects/{project_id}/compliance/profile`
- `POST /api/v1/projects/{project_id}/compliance/profile`
- `GET /api/v1/projects/{project_id}/compliance/audit`

### Integrations Wizard

The Intake/Connections layer now supports managed connection flows:

- OAuth start and callback scaffolding
- Encrypted API-key and token storage
- Connection listing/status/health endpoints
- MCP server connection and tool discovery stubs
- Compliance-gated external writes

Endpoints:

- `POST /api/v1/intake/connections/oauth/start`
- `GET /api/v1/intake/oauth/{connector_type}/callback`
- `POST /api/v1/intake/connections`
- `GET /api/v1/intake/connections/{project_id}`
- `GET /api/v1/intake/connections/{project_id}/{connector_type}/status`
- `GET /api/v1/intake/connections/{project_id}/{connector_type}/health`
- `GET /api/v1/intake/connections/{project_id}/mcp/tools`

### Frontend Project OS

The Next.js dashboard at `frontend/` exposes:

- Runtime, graph, compliance, and connection summary cards
- Multipart document upload panel
- Graph build panel
- Orchestrator run panel
- Compliance profile and audit controls
- Connections panel with Intake Wizard

Run locally:

```bash
cd frontend
npm install
npm run dev
```

For direct Python execution:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=backend/app uvicorn main:app --reload
```

## 6. Parallel Development Instructions

- **Cursor:** Final integration, local running, git.
- **Claude:** Deep agent logic and LangGraph.
- **Grok:** Master framework coordination.
- **Lovable:** Rapid full-stack UI and basic backend generation.
- **Manus:** Autonomous tests for OAuth flows, MCP connectors, and ingestion.

Next component priority: Phase 1 PDF ingestion parser.
