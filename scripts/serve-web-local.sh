#!/usr/bin/env sh
set -eu

# Serve the composed local web shell from build/web-local.
# Usage: WEB_PORT=8080 scripts/serve-web-local.sh

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/lib/common.sh"

cd "$REPO_ROOT"

require_cmd python3

echo "web local: serving http://127.0.0.1:${WEB_PORT:-8080}"
# Flutter web uses the hash URL strategy here, so no SPA rewrite is needed.
python3 -m http.server "${WEB_PORT:-8080}" --bind 127.0.0.1 --directory "$REPO_ROOT/build/web-local"
