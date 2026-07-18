# Assen Platform — common entry points for the scattered scripts/*.sh (POSIX/CI)
# and scripts/*.ps1 (Windows dev host, no WSL — ADR-10) scripts, so `just <recipe>`
# is the same command regardless of which host you're on.
#
# Requires just >= 1.17 (OS-conditional recipe attributes: [windows]/[unix]).
# Install: https://github.com/casey/just#installation
#
# No `set windows-shell` override — every recipe body below is a single external
# command invocation (no &&/cd shell built-ins on the [windows] side), so it runs
# identically whether just picks sh (Git Bash, already a dependency of every
# scripts/*.sh script on this host) or cmd.exe as its default Windows shell.

# List available recipes.
default:
    @just --list

# Windows: server\.venv-win create/repair + migrate + seed_demo + web npm ci (scripts/bootstrap-win.ps1).
[windows]
bootstrap:
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/bootstrap-win.ps1

# POSIX/CI: server uv sync + web npm ci (deps only — no service boot, see `just up`).
[unix]
bootstrap:
    cd server && uv sync --frozen
    cd web && npm ci --legacy-peer-deps

# Diagnose the ".venv-win lock" trap: a running python/daphne holds server\.venv-win\Scripts\*.pyd, so `uv sync` fails.
[windows]
doctor:
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/doctor-win.ps1

# This trap is Windows-only (server\.venv-win) — nothing to diagnose on POSIX.
[unix]
doctor:
    @echo "doctor: this trap is Windows-only (server/.venv-win) — nothing to diagnose here."

# Boot postgres/redis/api/celery-worker/celery-beat (docker compose) + smoke-local.sh.
up:
    sh scripts/up-local.sh

# Smoke an already-running local stack (subset of `just up`'s checks).
smoke:
    sh scripts/smoke-local.sh

# Flutter web/APK + backend image build (BUILD_* env toggles — see scripts/build-local.sh).
build:
    sh scripts/build-local.sh

# Server verify (AGENTS.md contract): ruff + mypy + pytest, via `uv run`.
[unix]
test:
    cd server && uv run ruff check .
    cd server && uv run mypy .
    cd server && uv run pytest

# Same, via server\.venv-win\Scripts\*.exe directly (uv is frequently missing from PATH in non-interactive Windows shells — see scripts/bootstrap-win.ps1's Resolve-UvExe).
[windows]
test:
    cd server && .venv-win/Scripts/ruff.exe check .
    cd server && .venv-win/Scripts/mypy.exe .
    cd server && .venv-win/Scripts/pytest.exe
