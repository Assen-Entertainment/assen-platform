#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/lib/common.sh"

cd "$REPO_ROOT"

COMMIT_SHA="${COMMIT_SHA:-$(short_commit_sha)}"
COMPOSE_ENV_FILE="${COMPOSE_ENV_FILE:-.omx/compose.env}"
export COMMIT_SHA
export COMPOSE_ENV_FILE

write_compose_env_file "$COMPOSE_ENV_FILE"

echo "local up: commit=${COMMIT_SHA}"
echo "local up: validating compose"
compose_env_run config -q

echo "local up: starting postgres/redis"
compose_env_run up -d postgres redis

echo "local up: building backend services"
compose_env_run build api celery-worker celery-beat

echo "local up: applying local Django migrations"
compose_env_run run --rm api uv run --no-sync python manage.py migrate --noinput

echo "local up: starting api/celery worker/celery beat"
compose_env_run up -d api celery-worker celery-beat

"$SCRIPT_DIR/smoke-local.sh"
