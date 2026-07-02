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
_api_attempt=1
while [ "$_api_attempt" -le 12 ]; do
  if curl -fsS "${API_URL}/healthz"; then
    printf '\n'
    break
  fi
  echo "local smoke: API not ready yet; retry ${_api_attempt}/12"
  _api_attempt=$((_api_attempt + 1))
  sleep 5
done
if [ "$_api_attempt" -gt 12 ]; then
  echo "error: API did not answer /healthz" >&2
  exit 1
fi

echo "local smoke: API /api/health"
curl -fsS "${API_URL}/api/health"
printf '\n'

# Domain-table probe: /api/creators queries a migration-less domain table, so a
# 200 page here proves `migrate --run-syncdb` actually provisioned the schema
# (a bare healthz cannot catch a missing-table regression).
echo "local smoke: API /api/creators (domain tables provisioned)"
_creators_body="$(curl -fsS "${API_URL}/api/creators")"
case "$_creators_body" in
  *'"items"'*) echo "local smoke: creators page ok" ;;
  *)
    echo "error: /api/creators did not return a page — domain tables missing (run-syncdb)?" >&2
    exit 1
    ;;
esac

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
