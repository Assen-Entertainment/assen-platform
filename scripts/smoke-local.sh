#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/lib/common.sh"

cd "$REPO_ROOT"

API_URL="${ASSEN_LOCAL_API_URL:-http://127.0.0.1:8000}"
POSTGRES_USER="${POSTGRES_USER:-assen}"
POSTGRES_DB="${POSTGRES_DB:-assen}"

require_cmd curl

local_compose() {
  if [ -f "${COMPOSE_ENV_FILE:-.omx/compose.env}" ]; then
    compose_env_run "$@"
  else
    compose_run "$@"
  fi
}

echo "local smoke: compose services"
local_compose ps

echo "local smoke: API /healthz"
curl -fsS "${API_URL}/healthz"
printf '\n'

echo "local smoke: API /api/health"
curl -fsS "${API_URL}/api/health"
printf '\n'

echo "local smoke: redis"
local_compose exec -T redis redis-cli ping

echo "local smoke: postgres"
local_compose exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"

echo "local smoke: celery worker"
_attempt=1
while [ "$_attempt" -le 6 ]; do
  if local_compose exec -T celery-worker uv run --no-sync celery -A config inspect ping --timeout=10; then
    echo "local smoke: done"
    exit 0
  fi
  echo "local smoke: celery not ready yet; retry ${_attempt}/6"
  _attempt=$((_attempt + 1))
  sleep 5
done

echo "error: celery worker did not answer ping" >&2
exit 1
