#!/usr/bin/env bash
# Production entrypoint: wait for Postgres, run Alembic migrations, start API.
set -euo pipefail

WAIT_TIMEOUT="${WAIT_TIMEOUT:-120}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-true}"

log() { echo "[entrypoint] $*"; }

wait_for_postgres() {
  if [[ -z "${DATABASE_URL:-}" ]]; then
    log "DATABASE_URL not set; skipping Postgres wait"
    return 0
  fi
  if [[ "${DATABASE_URL}" != *"postgresql"* ]] && [[ "${DATABASE_URL}" != *"postgres"* ]]; then
    log "Non-Postgres DATABASE_URL; skipping wait"
    return 0
  fi

  log "Waiting for Postgres (timeout ${WAIT_TIMEOUT}s)..."
  python3 <<'PY'
import os
import sys
import time

url = os.environ.get("DATABASE_URL", "")
timeout = int(os.environ.get("WAIT_TIMEOUT", "120"))
deadline = time.time() + timeout

while time.time() < deadline:
    try:
        import asyncio
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text

        async def probe():
            engine = create_async_engine(url, pool_pre_ping=True)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()

        asyncio.run(probe())
        print("[entrypoint] Postgres is ready")
        sys.exit(0)
    except Exception as exc:
        print(f"[entrypoint] Postgres not ready: {exc}", flush=True)
        time.sleep(2)

print("[entrypoint] Postgres wait timed out", file=sys.stderr)
sys.exit(1)
PY
}

run_migrations() {
  if [[ "${RUN_MIGRATIONS}" != "true" ]]; then
    log "RUN_MIGRATIONS=false; skipping Alembic"
    return 0
  fi
  if [[ ! -f /app/alembic.ini ]]; then
    log "alembic.ini not found; skipping migrations"
    return 0
  fi
  log "Running Alembic migrations..."
  cd /app
  python3 -m alembic upgrade head
  log "Migrations complete"
}

wait_for_postgres
run_migrations

log "Starting: $*"
exec "$@"
