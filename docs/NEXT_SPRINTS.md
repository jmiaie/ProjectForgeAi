# ProjectForge AI Next Sprints

This roadmap is ordered by dependency and integration value. Multiple agents can work in parallel where noted.

## Sprint 1: Phase 1 Document Ingestion

**Status:** Active. PDF, email, Office, image, manifest, multipart upload, mbox, attachments, and nested `.eml` chains are in place.

Build the file ingestion foundation that feeds Locus and OMPA with high-confidence source chunks.

- PDF parser: text, page metadata, source hashes, warnings. **Done.**
- Image parser: OCR-ready interface, EXIF metadata, confidence warnings. **OCR + metadata done (Tesseract optional).**
- Email parser: `.eml` headers, body, attachment metadata. **Done with nested attachment ingestion.**
- Office parser: DOCX, XLSX, PPTX text extraction. **Table-aware XLSX + heading/table DOCX + slide-labeled PPTX done.**
- Ingestion manifest: per-file status, parser warnings, chunk counts, source hashes. **Done.**
- Upload endpoint: multipart `UploadFile` support. **Done at `POST /api/v1/projects/upload`.**

## Sprint 2: Project Graph Builder

**Status:** Active. Manifest projection, enrichment, Neo4j bootstrap/migrations, orphan cleanup, and graph mutation APIs are in place.

Convert extracted document facts into the living project graph.

- Define graph schema: project, stakeholder, company, task, milestone, document, decision, risk, dependency. **Starter labels added.**
- Add Neo4j adapter and migrations/bootstrap. **Versioned bootstrap + orphan cleanup on rebuild done.**
- Build document-to-graph extraction service through LLMRouter. **Heuristic + optional LLM enrichment with JSON validation done.**
- Store graph provenance: every node/edge links back to source chunks. **Manifest + DERIVED_FROM enrichment provenance added.**
- Add graph status endpoint and minimal query endpoint. **Build/enrich/mutation endpoints done.**

## Sprint 3: LangGraph Orchestrator

**Status:** Active. Specialist workflow, per-step checkpoints, run history, resume, and API endpoints are in place; deeper LangGraph branching remains next.

Turn ingestion + graph into agentic project operations.

- Implement orchestrator state model. **Done.**
- Add specialist agent nodes: intake analyst, scheduler, risk analyst, compliance reviewer, template generator. **Done.**
- Add tool bindings for Locus retrieve, OMPA record/session, integrations, and graph queries. **Done.**
- Add deterministic checkpoints and audit events. **Per-step checkpoints + run history done; LangGraph graph pending.**
- Add `/api/v1/orchestrator/run` endpoint. **Done with `/orchestrator/runs` history.**

## Sprint 4: Compliance Enforcer

**Status:** Active. Profile persistence, redaction, policy checks, memory/external-write gates, and audit APIs are in place.

Make HIPAA/legal/SOC2/GDPR controls first-class.

- Expand compliance profiles by project category. **Done.**
- Add policy checks before LLM calls and integration writes. **Done.**
- Add redaction hooks for PHI/PII-sensitive chunks. **Done.**
- Gate self-learning and memory writes by compliance category. **Done.**
- Add audit log model and API. **Done.**

## Sprint 5: Integrations Wizard

**Status:** Active. OAuth PKCE scaffolding, encrypted storage, API-key flows, MCP HTTP discovery, health checks, and live connection UI are in place.

Upgrade the starter Intake Wizard into real connections.

- OAuth 2.0/PKCE start/callback routes. **PKCE + state store + mock/real token exchange done.**
- API-key connector storage with encryption. **Done.**
- MCP server discovery, auth, and tool registry. **HTTP discovery fallback done; live MCP SDK pending.**
- Connection health checks. **Done with frontend live health cards.**
- Frontend connection cards with live status. **Done.**

## Sprint 6: Frontend Project OS

**Status:** Active. Runnable Next.js shell with editable graph, workbench, orchestrator artifacts/history, automations controls, and live connections UI.

Expose the living project graph and agent workflows.

- Project dashboard shell. **Done.**
- React Flow graph viewer. **Editable nodes + DEPENDS_ON/RELATES_TO linking done.**
- Chat/workbench tied to Locus + graph context. **Done.**
- Document ingestion status panel. **Done.**
- Template and report generation UI. **Orchestrator artifact view done.**
- Gantt/timeline placeholder fed by graph milestones. **Starter done.**

## Sprint 7: Temporal Automations

**Status:** Active. Local persistence, scheduling, worker process, dead letters, and optional Temporal Schedule sync are in place.

Add durable project workflows.

- Timed emails and reminders. **Done.**
- Recurring project status reports. **Done.**
- Integration sync jobs. **Done.**
- Human approval gates. **Done with UI approve action.**
- Retry/dead-letter strategy. **Done.**
- Real Temporal worker + docker services. **Done.**
- Schedule evaluation + Temporal Schedule sync. **Done.**

## Recommended Immediate Next Move

Proceed with **Phase 2 agent depth**:

1. Replace sequential orchestrator loop with LangGraph state machine + branching.
2. Wire real Google/Microsoft OAuth client credentials for production token exchange.
3. Add live MCP Python SDK discovery when server exposes standard MCP transport.
4. Upgrade timeline/Gantt UI with editable milestone dates from graph properties.
