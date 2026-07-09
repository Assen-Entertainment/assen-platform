# Assen Platform backend image. Built and smoke-tested in CI (local Docker is
# unavailable on the dev host). Uses uv for reproducible dependency installs.
FROM python:3.12-slim AS base

ARG COMMIT_SHA=unknown

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    COMMIT_SHA=${COMMIT_SHA}

# uv provides fast, locked installs; copied from its official image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

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

EXPOSE 8000

# Daphne serves the ASGI app so HTTP and the Channels WebSocket stack (config.asgi)
# share one server — a WSGI server (gunicorn) would drop the `websocket` protocol
# entirely. Static files are unaffected: the API is JSON + admin only and was never
# served by the app server (no whitenoise); the ALB/CDN or `collectstatic` target
# owns static delivery. Settings module comes from the environment
# (DJANGO_SETTINGS_MODULE). Single-process here; horizontal scale-out needs the
# shared channels-redis layer (CHANNEL_LAYERS_BACKEND=redis, E10) so socket groups
# span workers.
CMD ["uv", "run", "--no-sync", "daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
