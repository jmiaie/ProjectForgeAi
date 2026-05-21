# ProjectForgeAi

Spec-driven project generator with versioned **forge recipes**. Turn structured inputs into reproducible, reviewable repository scaffolding—not one-off chat output.

## Status

Early development (v0.1). The CLI ships one recipe (`minimal`) and local directory output. See [vision & v1 scope](docs/vision.md).

## Quick start

**Requirements:** Node.js 20+

```bash
git clone https://github.com/jmiaie/ProjectForgeAi.git
cd ProjectForgeAi
npm ci
npm run build
npm test
```

### Run the hello-world forge

```bash
npm run forge -- run --recipe minimal --output ./my-new-project --name my-app
```

This creates a small Node.js project (README, `package.json`, CI workflow) plus `forge.manifest.json` for audit.

### List recipes

```bash
npm run forge -- list
```

## Documentation

| Doc | Description |
|-----|-------------|
| [docs/vision.md](docs/vision.md) | Problem, v1 scope, principles |
| [docs/architecture.md](docs/architecture.md) | Components and forge lifecycle |
| [docs/adr/001-execution-model.md](docs/adr/001-execution-model.md) | Safety defaults (PR-only, no auto-push) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |

## Project layout

```
├── src/              # CLI and forge engine
├── templates/        # Versioned recipe templates
├── docs/             # Vision, architecture, ADRs
└── .github/workflows # CI + smoke forge
```

## CLI options

```
forge run --recipe <name> --output <dir> [--name <project>] [--force]
```

- `--force` — Allow writing into a non-empty directory (see ADR-001).
- Output is **local only** in v1; you commit and open a PR yourself.

## Roadmap (after v1)

- Spec / LLM planner with validation gate
- GitHub PR automation (least-privilege)
- Additional recipes (API service, monorepo, etc.)
- Integration with issue trackers (Notion, Linear, …)

## License

MIT — see [LICENSE](LICENSE).
