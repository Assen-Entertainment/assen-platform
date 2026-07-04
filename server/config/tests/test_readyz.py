"""Tests for the /readyz readiness probe (R4-W2, ASS-242).

Readiness differs from liveness (/healthz): it reports 200 only when the process
can actually serve — here, when the database connection is reachable — and 503
otherwise, so an orchestrator drains the task instead of routing to it.
"""

from __future__ import annotations

import pytest
from django.db import connection
from django.db.utils import OperationalError
from django.test import Client


@pytest.mark.django_db
def test_readyz_ready_when_db_reachable(client: Client) -> None:
    """DB up → 200, status "ready", and the version/commit metadata is surfaced."""
    res = client.get("/readyz")

    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"] == "ok"
    assert body["version"] == "0.1.0"
    assert isinstance(body["commit"], str)
    assert body["commit"]


def test_readyz_reports_not_ready_when_db_down(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing DB connection degrades to 503 (never a 500), naming the check."""

    def _boom() -> None:
        raise OperationalError("database is unavailable")

    monkeypatch.setattr(connection, "ensure_connection", _boom)

    res = client.get("/readyz")

    assert res.status_code == 503
    body = res.json()
    assert body["status"] == "not ready"
    assert body["checks"]["database"] == "error"
