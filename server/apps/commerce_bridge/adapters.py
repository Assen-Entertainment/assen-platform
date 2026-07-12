"""Provider-agnostic webhook adapters for the hosted-commerce bridge.

Each hosted commerce provider signs webhooks differently and ships a different payload
shape. An adapter (a) verifies the signature against the shared secret — **fail-closed**
— and (b) normalises the payload into a :class:`NormalizedEvent` the ingest service
consumes. Only a generic HMAC adapter exists today (used by tests and by a headless
sender that already emits the canonical shape); real Cafe24/Imweb adapters translate
their own header/body into this same contract when a provider is chosen.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedEvent:
    """A hosted-commerce webhook normalised to exactly what the bridge needs."""

    event_id: str
    # order_paid / order_shipped / order_cancelled / order_refunded
    event_type: str
    external_order_id: str
    # The provider's echo of the product's creator tag (mapped to a Creator by handle).
    creator_ref: str
    buyer_ref: str
    amount: int
    currency: str = "KRW"


class WebhookVerificationError(Exception):
    """Raised when a webhook signature/secret/body check fails (fail-closed)."""


class CommerceWebhookAdapter(ABC):
    """Verify + parse a hosted-commerce provider's webhook."""

    @abstractmethod
    def verify(
        self, *, secret: str, headers: Mapping[str, str], raw_body: bytes
    ) -> None:
        """Raise :class:`WebhookVerificationError` unless the signature is valid."""

    @abstractmethod
    def parse(self, *, raw_body: bytes) -> NormalizedEvent:
        """Parse the raw body into a :class:`NormalizedEvent` (assumes verify passed)."""


class GenericHmacAdapter(CommerceWebhookAdapter):
    """HMAC-SHA256 signed, already-normalised JSON body — the reference adapter.

    Signature = hex ``HMAC-SHA256(secret, raw_body)`` in the ``X-Assen-Signature``
    header (compared in constant time). Body = the :class:`NormalizedEvent` fields as
    JSON. Real provider adapters translate their own header/shape into this contract.
    """

    # Header keys are looked up lower-cased (the API layer lower-cases the header map).
    SIGNATURE_HEADER = "x-assen-signature"

    def verify(self, *, secret: str, headers: Mapping[str, str], raw_body: bytes) -> None:
        """Reject unless the HMAC signature matches (empty secret → reject)."""
        if not secret:
            raise WebhookVerificationError("no webhook secret configured")
        provided = (headers.get(self.SIGNATURE_HEADER) or "").strip()
        expected = hmac.new(
            secret.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()
        if not provided or not hmac.compare_digest(provided, expected):
            raise WebhookVerificationError("signature mismatch")

    def parse(self, *, raw_body: bytes) -> NormalizedEvent:
        """Parse the canonical JSON body; a malformed body is a verification error."""
        try:
            data = json.loads(raw_body.decode("utf-8"))
            return NormalizedEvent(
                event_id=str(data["event_id"]),
                event_type=str(data["event_type"]),
                external_order_id=str(data["external_order_id"]),
                creator_ref=str(data.get("creator_ref", "")),
                buyer_ref=str(data.get("buyer_ref", "")),
                amount=int(data.get("amount", 0)),
                currency=str(data.get("currency", "KRW")),
            )
        except (ValueError, KeyError, TypeError, UnicodeDecodeError) as exc:
            raise WebhookVerificationError("invalid webhook body") from exc


# Registry of supported providers. cafe24/imweb intentionally absent until a provider
# is chosen — an unsupported provider is refused rather than silently mis-parsed.
_ADAPTERS: dict[str, CommerceWebhookAdapter] = {"generic": GenericHmacAdapter()}


def adapter_for(provider: str) -> CommerceWebhookAdapter | None:
    """Return the adapter for ``provider``, or ``None`` if unsupported."""
    return _ADAPTERS.get(provider)
