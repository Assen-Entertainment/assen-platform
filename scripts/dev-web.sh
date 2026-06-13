#!/usr/bin/env sh
set -eu

# Run a Flutter fan/operator app in web dev mode with hot restart (ASS-145).
# Usage: scripts/dev-web.sh [fan|operator] [port]
#
# Flutter web supports hot RESTART (press R in the attached session), not the
# stateful hot reload of mobile — but it still beats the static build/serve
# loop. The composed static shell (build-web-local.sh / serve-web-local.sh)
# stays the integration/handoff QA path; this is the iterative dev path.

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/lib/common.sh"

require_cmd flutter

APP="${1:-fan}"
PORT="${2:-8081}"
case "$APP" in
  fan) APP_DIR="$REPO_ROOT/apps/fan_app" ;;
  operator) APP_DIR="$REPO_ROOT/apps/operator_app" ;;
  *)
    echo "usage: scripts/dev-web.sh [fan|operator] [port]" >&2
    exit 2
    ;;
esac

cd "$APP_DIR"
echo "dev-web: $APP on http://127.0.0.1:${PORT} (press R to hot restart, q to quit)"
exec flutter run -d web-server --web-hostname 127.0.0.1 --web-port "$PORT"
