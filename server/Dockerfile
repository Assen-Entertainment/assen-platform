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
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy the application source and install the project itself.
COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8000

# Gunicorn serves the WSGI app; settings module is provided via the environment.
CMD ["uv", "run", "--no-sync", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
