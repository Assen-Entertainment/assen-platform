#!/usr/bin/env sh
set -eu

# Build the local web shell: Vite landing at `/` and Flutter fan app at `/app/`.
# Usage: scripts/build-web-local.sh

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/lib/common.sh"

cd "$REPO_ROOT"

require_cmd npm
require_cmd flutter

WEB_LOCAL_DIR="$REPO_ROOT/build/web-local"
LANDING_DIR="$REPO_ROOT/landing"
FAN_APP_DIR="$REPO_ROOT/apps/fan_app"
FAN_APP_BUILD_DIR="$FAN_APP_DIR/build/web"

echo "web local: building landing"
cd "$LANDING_DIR"
npm ci
npm run build

echo "web local: building fan_app for /app/"
cd "$FAN_APP_DIR"
# Disable the service worker for local composition so stale Flutter shell files
# cannot mask the current landing/app handoff while iterating.
flutter build web --base-href /app/ --pwa-strategy none

echo "web local: composing build/web-local"
cd "$REPO_ROOT"
rm -rf "$WEB_LOCAL_DIR"
mkdir -p "$WEB_LOCAL_DIR/app"
cp -R "$LANDING_DIR/dist/." "$WEB_LOCAL_DIR/"
cp -R "$FAN_APP_BUILD_DIR/." "$WEB_LOCAL_DIR/app/"

echo "web local: output $WEB_LOCAL_DIR"
echo "web local: next run scripts/serve-web-local.sh and open http://127.0.0.1:${WEB_PORT:-8080}"
