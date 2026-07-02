#!/usr/bin/env bash
# setup_pretendard.sh — stage Pretendard static weights for app bundling.
#
# WHY: the design SSOT (docs/design/tokens.v2.json) uses Pretendard, but the app
# never bundled the font, and the generated typography still carries the legacy
# "Cafe24 Ssurround" face from the OLD docs/design/tokens.json (see G012 below).
# This script downloads the OFL Pretendard release and drops the four weights
# the type scale needs into packages/ui_kit/fonts/.
#
# RUN (WSL, from repo root):  bash tools/fonts/setup_pretendard.sh
# Then: add the printed `fonts:` block to packages/ui_kit/pubspec.yaml under
# `flutter:`, run `flutter pub get`, and re-run golden tests (human-gated,
# CONSTRAINTS #31) since the rendered face changes.
#
# LICENSE: Pretendard is SIL OFL 1.1. The script also copies LICENSE into
# packages/ui_kit/fonts/ — keep it; bundling requires shipping the licence.
set -euo pipefail

VER="${PRETENDARD_VERSION:-1.3.9}"
URL="https://github.com/orioncactus/pretendard/releases/download/v${VER}/Pretendard-${VER}.zip"
DEST="packages/ui_kit/fonts"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$DEST"
echo "Downloading Pretendard v${VER}…"
curl -fsSL "$URL" -o "$TMP/pretendard.zip"
unzip -oq "$TMP/pretendard.zip" -d "$TMP"

copied=0
for w in Regular Medium SemiBold Bold; do
  src="$(find "$TMP" -name "Pretendard-$w.otf" -print -quit || true)"
  if [ -n "$src" ]; then cp "$src" "$DEST/"; copied=$((copied+1)); fi
done
lic="$(find "$TMP" -iname 'LICENSE*' -print -quit || true)"
[ -n "$lic" ] && cp "$lic" "$DEST/LICENSE"

echo "Copied $copied weight(s) to $DEST:"
ls -1 "$DEST"

cat <<'YAML'

# ── add to packages/ui_kit/pubspec.yaml under `flutter:` ────────────────────
#   uses-material-design: true            # (existing line)
  fonts:
    - family: Pretendard
      fonts:
        - asset: fonts/Pretendard-Regular.otf
          weight: 400
        - asset: fonts/Pretendard-Medium.otf
          weight: 500
        - asset: fonts/Pretendard-SemiBold.otf
          weight: 600
        - asset: fonts/Pretendard-Bold.otf
          weight: 700
# ────────────────────────────────────────────────────────────────────────────
YAML
echo "Done. Family name 'Pretendard' matches tokens.v2.json typography.fontFamily."
