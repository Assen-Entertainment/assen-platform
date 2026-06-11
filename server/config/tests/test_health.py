"""Tests for the Ninja health endpoint. No database access required."""

from __future__ import annotations

from django.test import Client


def test_health_returns_ok(client: Client) -> None:
    """`/api/health` responds 200 with status, version, and commit fields."""
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"
    # Commit is environment-dependent but must always be a non-empty string.
    assert isinstance(body["commit"], str)
    assert body["commit"]
