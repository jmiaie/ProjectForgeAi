# Air-gapped update bundles

Offline workflow for self-hosted / air-gapped ProjectForge AI deployments.

## Build bundle (online build machine)

```bash
python3 scripts/build_airgap_bundle.py --version 14.0.0
```

Options:

| Flag | Description |
|------|-------------|
| `--output-dir` | Output directory (default: `dist/airgap`) |
| `--skip-wheels` | Skip `pip download` (source-only bundle) |

Produces `dist/airgap/projectforge-airgap-{version}-{sha}.tar.gz` containing:

- `source/` — application snapshot with checksums
- `wheels/` — offline Python dependencies (unless skipped)
- `helm/` — Kubernetes chart
- `onprem/` — Compose production overlay
- `MANIFEST.json` — file manifest and metadata
- `apply_airgap_bundle.py` — apply helper

Transfer the `.tar.gz` to the air-gapped environment via approved media.

## Apply bundle (offline target)

```bash
python3 scripts/apply_airgap_bundle.py dist/airgap/projectforge-airgap-14.0.0-abc1234.tar.gz \
  --target-dir /opt/projectforge
```

Options:

| Flag | Description |
|------|-------------|
| `--target-dir` | Install root (default: repository root) |
| `--skip-pip` | Skip offline pip install from bundled wheels |

After apply:

1. Review `.env` / `deploy/onprem/.env.prod.example`
2. Restart via Compose or Helm (see `AIRGAP_APPLY.json` in target dir)

## Verify deployment

```bash
curl https://projectforge.internal/health
curl https://projectforge.internal/api/v1/deploy/status
```

`build_info` in the health response confirms the applied bundle version.

## Related

- [../onprem/README.md](../onprem/README.md) — Docker Compose on-prem
- [../helm/projectforge/README.md](../helm/projectforge/README.md) — Kubernetes Helm chart
