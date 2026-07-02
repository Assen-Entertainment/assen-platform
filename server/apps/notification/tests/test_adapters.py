"""Acceptance tests for the mock push-notification adapter (#16).

Covers: a mock send is recorded and reported accepted, and an empty token is
rejected (mirrors the real provider contract).
"""

from __future__ import annotations

from apps.notification.adapters import (
    MockNotificationAdapter,
    PushMessage,
)


def test_mock_send_is_recorded_and_accepted() -> None:
    """A valid push is appended to the outbox and reported accepted."""
    adapter = MockNotificationAdapter()
    result = adapter.send(
        PushMessage(token="device-1", title="hi", body="visit logged")
    )
    assert result.accepted is True
    assert result.message_id == "mock-1"
    assert len(adapter.sent) == 1
    assert adapter.sent[0].token == "device-1"


def test_mock_rejects_empty_token() -> None:
    """An empty device token is rejected and not recorded."""
    adapter = MockNotificationAdapter()
    result = adapter.send(PushMessage(token="", title="x", body="y"))
    assert result.accepted is False
    assert adapter.sent == []
