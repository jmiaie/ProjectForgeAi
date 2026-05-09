# ProjectForge AI Next Sprints

This roadmap is ordered by dependency and integration value. Multiple agents can work in parallel where noted.

## Sprint 1: Phase 1 Document Ingestion

**Status:** Active. Starter PDF, email, Office, image metadata, manifest, and multipart upload paths are in place.

Build the file ingestion foundation that feeds Locus and OMPA with high-confidence source chunks.

- PDF parser: text, page metadata, source hashes, warnings. **Starter done.**
- Image parser: OCR-ready interface, EXIF metadata, confidence warnings. **Metadata starter done; OCR pending.**
- Email parser: `.eml` headers, body, attachment metadata. **Starter done; mailbox exports pending.**
- Office parser: DOCX, XLSX, PPTX text extraction. **Starter done; table fidelity pending.**
- Ingestion manifest: per-file status, parser warnings, chunk counts, source hashes. **Starter done.**
- Upload endpoint: multipart `UploadFile` support. **Starter done at `POST /api/v1/projects/upload`.**

Parallel owners:
- Parser agents can each own one file type.
- Backend agent owns manifest + upload endpoint.
- Test agent owns fixture corpus and golden output checks.

## Sprint 2: Project Graph Builder

Convert extracted document facts into the living project graph.

- Define graph schema: project, stakeholder, company, task, milestone, document, decision, risk, dependency.
- Add Neo4j adapter and migrations/bootstrap.
- Build document-to-graph extraction service through LLMRouter.
- Store graph provenance: every node/edge links back to source chunks.
- Add graph status endpoint and minimal query endpoint.

Parallel owners:
- Graph schema agent.
- Neo4j adapter agent.
- Extraction prompt/provenance agent.

## Sprint 3: LangGraph Orchestrator

Turn ingestion + graph into agentic project operations.

- Implement orchestrator state model.
- Add specialist agent nodes: intake analyst, scheduler, risk analyst, compliance reviewer, template generator.
- Add tool bindings for Locus retrieve, OMPA record/session, integrations, and graph queries.
- Add deterministic checkpoints and audit events.
- Add `/api/v1/orchestrator/run` endpoint.

Parallel owners:
- LangGraph agent.
- Tooling adapter agent.
- Audit/checkpoint agent.

## Sprint 4: Compliance Enforcer

Make HIPAA/legal/SOC2/GDPR controls first-class.

- Expand compliance profiles by project category.
- Add policy checks before LLM calls and integration writes.
- Add redaction hooks for PHI/PII-sensitive chunks.
- Gate self-learning and memory writes by compliance category.
- Add audit log model and API.

Parallel owners:
- Policy model agent.
- Redaction agent.
- Audit persistence agent.

## Sprint 5: Integrations Wizard

Upgrade the starter Intake Wizard into real connections.

- OAuth 2.0/PKCE start/callback routes.
- API-key connector storage with encryption.
- MCP server discovery, auth, and tool registry.
- Connection health checks.
- Frontend connection cards with live status.

Parallel owners:
- OAuth agent.
- MCP agent.
- Frontend wizard agent.

## Sprint 6: Frontend Project OS

Expose the living project graph and agent workflows.

- Project dashboard shell.
- React Flow graph viewer.
- Chat/workbench tied to Locus + graph context.
- Document ingestion status panel.
- Template and report generation UI.
- Gantt/timeline placeholder fed by graph milestones.

Parallel owners:
- Dashboard/UI agent.
- Graph visualization agent.
- Chat/workbench agent.

## Sprint 7: Temporal Automations

Add durable project workflows.

- Timed emails and reminders.
- Recurring project status reports.
- Integration sync jobs.
- Human approval gates.
- Retry/dead-letter strategy.

Parallel owners:
- Temporal worker agent.
- Workflow definitions agent.
- Notification/integration agent.

## Recommended Immediate Next Move

Proceed with the rest of **Sprint 1**:

1. Add multipart upload support to `/api/v1/projects/`.
2. Add image/email/Office parser interfaces.
3. Add ingestion manifest persistence.
4. Feed successful chunks into Locus and parser warnings/decisions into OMPA.

That gives every downstream phase a reliable, provenance-rich source of truth.
