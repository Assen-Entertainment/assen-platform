#!/usr/bin/env sh

# Shared helpers for Assen Platform local/deploy scripts.

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "error: required command not found: $1" >&2
    exit 1
  fi
}

short_commit_sha() {
  git rev-parse --short=12 HEAD 2>/dev/null || printf '%s\n' unknown
}

full_commit_sha() {
  git rev-parse HEAD 2>/dev/null || printf '%s\n' unknown
}

docker_cmd() {
  if [ -n "${DOCKER:-}" ]; then
    printf '%s\n' "$DOCKER"
    return
  fi
  if [ -x "/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe" ]; then
    printf '%s\n' "/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe"
    return
  fi
  if command -v docker >/dev/null 2>&1; then
    printf '%s\n' docker
    return
  fi
  echo "error: docker CLI not found; set DOCKER=/path/to/docker" >&2
  exit 1
}

docker_run() {
  _docker_bin="$(docker_cmd)"
  "$_docker_bin" "$@"
}

compose_run() {
  docker_run compose "$@"
}

write_compose_env_file() {
  _compose_env_file="${1:-.omx/compose.env}"
  mkdir -p "$(dirname -- "$_compose_env_file")"
  {
    printf 'COMMIT_SHA=%s\n' "${COMMIT_SHA:-$(short_commit_sha)}"
    printf 'POSTGRES_DB=%s\n' "${POSTGRES_DB:-assen}"
    printf 'POSTGRES_USER=%s\n' "${POSTGRES_USER:-assen}"
    printf 'POSTGRES_PASSWORD=%s\n' "${POSTGRES_PASSWORD:-assen}"
  } >"$_compose_env_file"
}

compose_env_run() {
  _compose_env_file="${COMPOSE_ENV_FILE:-.omx/compose.env}"
  compose_run --env-file "$_compose_env_file" "$@"
}

require_clean_worktree() {
  if ! git diff --quiet --exit-code || ! git diff --cached --quiet --exit-code; then
    echo "error: worktree has uncommitted tracked changes" >&2
    git status --short >&2
    exit 1
  fi
}
