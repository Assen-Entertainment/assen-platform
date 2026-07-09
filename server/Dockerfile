# Assen Platform backend image. Built and smoke-tested in CI (local Docker is
# unavailable on the dev host). Uses uv for reproducible dependency installs.
#
# Base/tool images are pinned by digest (supply-chain hardening) — a moved tag
# (e.g. a repushed `latest` or `3.12-slim`) cannot silently change what ships.
# Digests resolved 2026-07-10 via the registry v2 manifest API (multi-arch
# index digest, not a single-arch image digest) — re-resolve and bump on the
# next planned base-image update:
#   curl -sI -H "Authorization: Bearer $TOKEN" \
#     -H "Accept: application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.list.v2+json" \
#     https://registry-1.docker.io/v2/library/python/manifests/3.12-slim | grep -i docker-content-digest
FROM python:3.12-slim@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf AS base

ARG COMMIT_SHA=unknown

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    COMMIT_SHA=${COMMIT_SHA}

# uv provides fast, locked installs; copied from its official image. Pinned to
# a specific release (not `:latest`) + its digest — `:latest` moves on every uv
# release, which would make the toolchain that produced a given image
# unreproducible. Bump the version deliberately; re-resolve the digest the same
# way as the base image above (repository astral-sh/uv, registry ghcr.io).
COPY --from=ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa /uv /uvx /bin/

WORKDIR /app

# Install dependencies first (cached layer) using only the lock + manifest.
# --extra realtime-redis pulls in channels-redis (pyproject optional-dependencies):
# prod runs multi-process behind CHANNEL_LAYERS_BACKEND=redis (E10), so the shared
# cross-worker layer must actually be installed in this image, not just dev-opt-in.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev --extra realtime-redis

# Copy the application source and install the project itself.
COPY . .
RUN uv sync --frozen --no-dev --extra realtime-redis

# Non-root runtime (parity with web/Dockerfile's `USER node`) — the app only needs to
# bind :8000 and read its own files, so it does not need root inside the container.
# Must run after every COPY/RUN above: appuser needs to own the fully materialized
# /app (source + .venv), and uv sync itself still runs as root, which is fine — build
# time and runtime privilege are separate concerns.
RUN groupadd --system appuser \
    && useradd --system --gid appuser --home-dir /app --no-create-home appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Readiness probe — checks the DB dependency (config.urls.readyz), not just process
# liveness (`/healthz`), so an orchestrator only routes traffic once a request can
# actually be served. No curl in python:slim, so this shells out to python like
# docker-compose.yml's api healthcheck (same interval/timeout/retries), but uses
# http.client instead of urllib.request (urlopen() raises HTTPError on the 503
# readyz returns when not ready) wrapped in try/except so a connection failure
# (API not up yet) exits 1 quietly instead of dumping a traceback into `docker
# inspect`. JSON exec form so \n is a real newline (shell form can't hold the
# indented try/except).
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
  CMD ["python", "-c", "import http.client,sys\ntry:\n    c=http.client.HTTPConnection('127.0.0.1',8000,timeout=3)\n    c.request('GET','/readyz')\n    sys.exit(0 if c.getresponse().status==200 else 1)\nexcept SystemExit:\n    raise\nexcept Exception:\n    sys.exit(1)"]

# Daphne serves the ASGI app so HTTP and the Channels WebSocket stack (config.asgi)
# share one server — a WSGI server (gunicorn) would drop the `websocket` protocol
# entirely. Static files are unaffected: the API is JSON + admin only and was never
# served by the app server (no whitenoise); the ALB/CDN or `collectstatic` target
# owns static delivery. Settings module comes from the environment
# (DJANGO_SETTINGS_MODULE). Single-process here; horizontal scale-out needs the
# shared channels-redis layer (CHANNEL_LAYERS_BACKEND=redis, E10) so socket groups
# span workers.
CMD ["uv", "run", "--no-sync", "daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
