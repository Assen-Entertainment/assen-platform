"""Test settings against real PostgreSQL (prod-parity dev testing).

Inherits everything from ``test.py`` (eager Celery, in-memory channel layer,
mock gates, etc.) but swaps the in-memory sqlite database for the local
docker-compose PostgreSQL, so the suite proves out on **production-parity
infrastructure** (schema built from the real migrations, Postgres constraint/
index/transaction semantics) — not just sqlite.

Run:  DATABASE_URL=postgres://assen:assen@localhost:5432/assen \
        pytest --ds=config.settings.test_pg
(pytest-django creates/drops a ``test_assen`` database on the server.)
"""

from __future__ import annotations

import environ

from .test import *  # noqa: F401,F403

env = environ.Env()

# Swap sqlite -> the compose Postgres. pytest-django builds a throwaway
# ``test_<name>`` DB by running the migrations, so this exercises the #25
# migration graph on the real engine.
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://assen:assen@localhost:5432/assen",
    ),
}
