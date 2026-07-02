#!/usr/bin/env sh
set -eu

# Run the Vite landing dev server with HMR (ASS-145).
# Usage: scripts/dev-landing.sh
#
# This is the live-edit path for the marketing landing (instant HMR). The
# composed static shell serves the `vite build` output instead; use this for
# iterating on landing markup/styles/motion.

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/lib/common.sh"

require_cmd npm

cd "$REPO_ROOT/landing"
# Install once if node_modules is missing; otherwise reuse for a fast start.
if [ ! -d node_modules ]; then
  npm ci
fi
echo "dev-landing: Vite dev server with HMR (default http://127.0.0.1:5173)"
exec npm run dev
