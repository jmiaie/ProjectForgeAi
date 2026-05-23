# ProjectForge AI Next Sprints

This roadmap is ordered by dependency and integration value. Multiple agents can work in parallel where noted.

## Sprint 1: Phase 1 Document Ingestion

**Status:** Active. Starter PDF, email, Office, image metadata, manifest, and multipart upload paths are in place.

Build the file ingestion foundation that feeds Locus and OMPA with high-confidence source chunks.

- PDF parser: text, page metadata, source hashes, warnings. **Starter done.**
- Image parser: OCR-ready interface, EXIF metadata, confidence warnings. **OCR + metadata done (Tesseract optional).**
- Email parser: `.eml` headers, body, attachment metadata. **Starter done; `.mbox` mailbox exports done.**
- Office parser: DOCX, XLSX, PPTX text extraction. **Starter done; table fidelity pending.**
- Ingestion manifest: per-file status, parser warnings, chunk counts, source hashes. **Starter done.**
- Upload endpoint: multipart `UploadFile` support. **Starter done at `POST /api/v1/projects/upload`.**

Parallel owners:
- Parser agents can each own one file type.
- Backend agent owns manifest + upload endpoint.
- Test agent owns fixture corpus and golden output checks.

## Sprint 2: Project Graph Builder

**Status:** Active. Starter manifest-to-graph projection, Neo4j adapter, in-memory fallback, and graph API endpoints are in place.

Convert extracted document facts into the living project graph.

- Define graph schema: project, stakeholder, company, task, milestone, document, decision, risk, dependency. **Starter labels added.**
- Add Neo4j adapter and migrations/bootstrap. **Adapter/fallback added; migrations pending.**
- Build document-to-graph extraction service through LLMRouter. **Heuristic + optional LLM enrichment starter done.**
- Store graph provenance: every node/edge links back to source chunks. **Manifest + DERIVED_FROM enrichment provenance added.**
- Add graph status endpoint and minimal query endpoint. **Starter endpoints added; enrich endpoint added.**

Parallel owners:
- Graph schema agent.
- Neo4j adapter agent.
- Extraction prompt/provenance agent.

## Sprint 3: LangGraph Orchestrator

**Status:** Active. Deterministic specialist workflow, run persistence, tool context, and API endpoints are in place; deeper LangGraph branching/checkpointing remains next.

Turn ingestion + graph into agentic project operations.

- Implement orchestrator state model. **Starter done.**
- Add specialist agent nodes: intake analyst, scheduler, risk analyst, compliance reviewer, template generator. **Starter done.**
- Add tool bindings for Locus retrieve, OMPA record/session, integrations, and graph queries. **Starter done.**
- Add deterministic checkpoints and audit events. **Run JSON persistence done; full checkpoints pending.**
- Add `/api/v1/orchestrator/run` endpoint. **Done.**

Parallel owners:
- LangGraph agent.
- Tooling adapter agent.
- Audit/checkpoint agent.

## Sprint 4: Compliance Enforcer

**Status:** Active. Profile persistence, redaction, policy checks, memory/external-write gates, and audit APIs are in place.

Make HIPAA/legal/SOC2/GDPR controls first-class.

- Expand compliance profiles by project category. **Starter done.**
- Add policy checks before LLM calls and integration writes. **Starter done.**
- Add redaction hooks for PHI/PII-sensitive chunks. **Starter PII/PHI patterns done.**
- Gate self-learning and memory writes by compliance category. **Memory write gating done.**
- Add audit log model and API. **Done.**

Parallel owners:
- Policy model agent.
- Redaction agent.
- Audit persistence agent.

## Sprint 5: Integrations Wizard

**Status:** Active. OAuth start/callback scaffolding, encrypted connection storage, API-key flows, MCP discovery stubs, and health/status endpoints are in place.

Upgrade the starter Intake Wizard into real connections.

- OAuth 2.0/PKCE start/callback routes. **Starter done; full PKCE token exchange pending.**
- API-key connector storage with encryption. **Done.**
- MCP server discovery, auth, and tool registry. **Starter done; live SDK discovery pending.**
- Connection health checks. **Done.**
- Frontend connection cards with live status.

Parallel owners:
- OAuth agent.
- MCP agent.
- Frontend wizard agent.

## Sprint 6: Frontend Project OS

**Status:** Active. Runnable Next.js shell, dashboard cards, ingestion, graph, orchestrator, compliance, and connections panels are in place.

Expose the living project graph and agent workflows.

- Project dashboard shell. **Done.**
- React Flow graph viewer. **Starter done with node detail drawer.**
- Chat/workbench tied to Locus + graph context. **Starter done.**
- Document ingestion status panel. **Starter done.**
- Template and report generation UI. **Orchestrator artifact view starter done.**
- Gantt/timeline placeholder fed by graph milestones. **Starter done.**

Parallel owners:
- Dashboard/UI agent.
- Graph visualization agent.
- Chat/workbench agent.

## Sprint 7: Temporal Automations

**Status:** Active. Local workflow persistence, reminders, recurring reports, integration sync jobs, approval gates, run history, Temporal worker process, and dispatch boundaries are in place.

Add durable project workflows.

- Timed emails and reminders. **Reminder starter done.**
- Recurring project status reports. **Orchestrator-backed starter done.**
- Integration sync jobs. **Health/sync starter done.**
- Human approval gates. **Done.**
- Retry/dead-letter strategy. **Retry scheduling + dead-letter queue starter done.**
- Real Temporal worker + docker services. **Worker, workflows, activities, and compose services added.**

Parallel owners:
- Temporal worker agent.
- Workflow definitions agent.
- Notification/integration agent.

## Recommended Immediate Next Move

Proceed with **production hardening**:

1. Improve LLM extraction prompts and structured JSON validation.
2. Add graph node editing and stakeholder/task updates in the UI.
3. Add table fidelity for Office parser exports.
4. Add Temporal schedule/cron wiring for recurring automations.
