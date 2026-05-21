# ADR-002: JSON Spec & Planner

## Status

Accepted (2026-05-21)

## Context

Forge runs need structured inputs so CI and humans can reproduce the same output. Free-form CLI flags do not scale to multi-field recipes.

## Decision

1. **ForgeSpec JSON Schema** at `schemas/forge-spec.schema.json`.
2. **`forge validate`** validates specs without writing files.
3. **`forge run --spec`** loads spec → validates → `planFromSpec()` → template vars.
4. Recipe is selected by `spec.recipe`; CLI `--recipe` is ignored when `--spec` is provided.

## Consequences

- Specs are versionable artifacts in git (`examples/specs/`).
- New recipes must extend schema `recipe` enum and document required fields.
- LLM planners must emit ForgeSpec-compatible JSON (future).

## Alternatives

| Alternative | Why not now |
|-------------|-------------|
| YAML specs | JSON sufficient for v0.2 |
| LLM-only input | No validation gate |
