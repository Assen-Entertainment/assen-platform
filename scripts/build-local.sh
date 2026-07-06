#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/lib/common.sh"

cd "$REPO_ROOT"

COMMIT_SHA="${COMMIT_SHA:-$(short_commit_sha)}"
COMPOSE_ENV_FILE="${COMPOSE_ENV_FILE:-.omx/compose.env}"
FLUTTER_APP="${FLUTTER_APP:-assen_mobile}"
BUILD_WEB="${BUILD_WEB:-1}"
BUILD_ANDROID_DEBUG="${BUILD_ANDROID_DEBUG:-1}"
BUILD_BACKEND_IMAGE="${BUILD_BACKEND_IMAGE:-1}"

export COMMIT_SHA
export COMPOSE_ENV_FILE

write_compose_env_file "$COMPOSE_ENV_FILE"

require_cmd dart
require_cmd flutter
require_cmd uv

echo "local build: commit=${COMMIT_SHA} flutter_app=${FLUTTER_APP}"

echo "local build: resolving Dart workspace"
dart pub get

echo "local build: resolving server dependencies"
(cd server && uv sync --frozen)

if [ "$BUILD_WEB" = "1" ]; then
  echo "local build: Flutter web (${FLUTTER_APP})"
  (cd "apps/${FLUTTER_APP}" && flutter build web --no-pub)
fi

if [ "$BUILD_ANDROID_DEBUG" = "1" ]; then
  echo "local build: Flutter Android debug APK (${FLUTTER_APP})"
  (cd "apps/${FLUTTER_APP}" && flutter build apk --debug --no-pub)
fi

if [ "$BUILD_BACKEND_IMAGE" = "1" ]; then
  echo "local build: backend Docker images"
  compose_env_run build api celery-worker celery-beat
fi

echo "local build: done"
