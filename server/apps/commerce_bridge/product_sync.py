"""Catalog sync contract — Assen keeps the product catalog as source of truth.

The creator attribution (``Product.creator``) is exactly why the catalog stays
authoritative in Assen even in the hybrid: the SaaS runs checkout/shipping, but the
settlement ledger must know which creator each product belongs to. This module defines
the export shape (Assen ``Product`` → provider-neutral dict) and a push-adapter
interface; a real provider adapter (Cafe24/Imweb API) implements ``push_product`` when a
provider is chosen. Until then the no-op adapter keeps the contract testable and the
platform track-agnostic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


def product_export(product: Any) -> dict[str, Any]:
    """Assen ``Product`` → a provider-neutral catalog payload.

    Includes the creator tag (by handle) so the SaaS can echo it back on order webhooks
    for settlement attribution. Carries no PII.
    """
    return {
        "id": str(product.id),
        "title": product.title,
        "price": product.price,
        "type": product.type,
        "status": product.status,
        "description": product.description,
        "creator_ref": product.creator.handle if product.creator_id else "",
    }


class CatalogSyncAdapter(ABC):
    """Push Assen's authoritative catalog to a hosted commerce provider."""

    @abstractmethod
    def push_product(self, *, payload: dict[str, Any]) -> str:
        """Upsert a product on the provider; return the provider's product id."""


class NoopCatalogSyncAdapter(CatalogSyncAdapter):
    """No-op adapter — used until a hosted provider is chosen. Pushes nothing."""

    def push_product(self, *, payload: dict[str, Any]) -> str:
        """Return an empty provider id — nothing is pushed."""
        return ""
