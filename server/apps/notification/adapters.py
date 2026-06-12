"""Push-notification adapter interface and a mock implementation (#16).

P0 ships the *interface* and an in-memory mock; the real FCM send path lands in
P5. Defining the boundary now lets domain code depend on
:class:`NotificationAdapter` (not on FCM directly), so the messaging-as-feed
constraint (#16: DB record + REST + push, one-way) is honoured and the transport
is swappable. The mock records sends so tests can assert delivery without a
network.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PushMessage:
    """A single push payload addressed to one device token.

    Kept minimal and transport-agnostic (title/body/data) so it maps cleanly onto
    FCM later without leaking FCM specifics into callers.
    """

    token: str
    title: str
    body: str
    data: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SendResult:
    """Outcome of a send attempt.

    ``message_id`` is provider-assigned on success; ``accepted`` lets callers
    branch without parsing provider errors.
    """

    accepted: bool
    message_id: str


class NotificationAdapter(ABC):
    """Transport boundary for outbound push notifications.

    Domain code targets this interface; the concrete transport (FCM in P5, mock
    in tests/dev) is injected, keeping send logic out of the domain.
    """

    @abstractmethod
    def send(self, message: PushMessage) -> SendResult:
        """Deliver one push message, returning the send outcome."""
        raise NotImplementedError


class MockNotificationAdapter(NotificationAdapter):
    """In-memory adapter that records sends instead of contacting FCM.

    Used in P0 (no real transport yet) and tests: every send is appended to
    :attr:`sent` so delivery can be asserted, and an empty token is rejected to
    mirror the real provider's contract.
    """

    def __init__(self) -> None:
        """Start with an empty outbox."""
        self.sent: list[PushMessage] = []

    def send(self, message: PushMessage) -> SendResult:
        """Record the message and return a synthetic accepted result.

        Rejecting an empty token here keeps the mock honest about the real
        provider's requirement, so a bug that drops the token is caught in tests.
        """
        if not message.token:
            return SendResult(accepted=False, message_id="")
        self.sent.append(message)
        return SendResult(accepted=True, message_id=f"mock-{len(self.sent)}")
