"""Hosted-commerce bridge API — inbound webhook receiver (fail-closed).

Unauthenticated by necessity (a hosted provider can't carry an Assen session) but every
request is HMAC-verified against ``COMMERCE_BRIDGE_WEBHOOK_SECRET`` before anything is
recorded, and the whole surface is off (503) unless ``ENABLE_COMMERCE_BRIDGE`` is set.
Idempotent: a duplicate delivery returns 200 with ``duplicate: true``.
"""

from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse
from ninja import Router

from apps.commerce_bridge.adapters import WebhookVerificationError
from apps.commerce_bridge.services import CommerceBridgeDisabled, ingest_webhook
from config.api import api

logger = logging.getLogger(__name__)

router = Router(tags=["commerce-bridge"])


@router.post("/commerce/{provider}/webhook", auth=None)
def commerce_webhook(request: HttpRequest, provider: str) -> HttpResponse:
    """Receive a hosted-commerce provider webhook. Fail-closed + signature-verified.

    503 when the bridge is disabled/unconfigured; 401 on a bad signature; 400 for an
    unsupported provider/event; 200 otherwise. The raw body is read for the HMAC check
    before any parsing.
    """
    raw_body = request.body
    headers = {key.lower(): value for key, value in request.headers.items()}
    try:
        order = ingest_webhook(provider=provider, headers=headers, raw_body=raw_body)
    except CommerceBridgeDisabled:
        return api.create_response(
            request,
            {"detail": "commerce bridge is disabled", "code": "CommerceBridgeDisabled"},
            status=503,
        )
    except WebhookVerificationError:
        # No echo of the reason — a signature failure must not leak which check failed.
        logger.warning(
            "commerce_bridge.webhook.rejected", extra={"provider": provider}
        )
        return api.create_response(request, {"detail": "invalid signature"}, status=401)
    except ValueError:
        return api.create_response(
            request, {"detail": "unsupported webhook"}, status=400
        )
    return api.create_response(
        request, {"status": "ok", "duplicate": order is None}, status=200
    )


api.add_router("/integrations", router)
