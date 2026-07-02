"""Public read API for membership tiers (SDLC 09 §4, E11/B2).

Read-only tier catalog. Subscriptions / recurring billing are **gated** (B4/B7)
and absent. Tiers per creator are a small bounded set, so the list is returned
whole (no pagination). Filter to a creator via ``?creator_id=``.
"""

from __future__ import annotations

import uuid

from django.http import HttpRequest
from ninja import Router, Schema

from apps.membership.models import MembershipTier
from config.api import api

tiers_router = Router(tags=["membership"])

# Hard cap on the unfiltered (global) list — the "small bounded set" assumption
# only holds per creator, so cap the cross-creator response defensively.
_MAX_TIERS = 100


class TierOut(Schema):
    """Membership tier (maps to the frontend ``MembershipTier`` type)."""

    id: uuid.UUID
    creator_id: uuid.UUID | None = None
    name: str
    price: int
    period: str
    benefits: list[str]
    badge: str
    featured: bool
    sort_order: int


def _tier_out(tier: MembershipTier) -> TierOut:
    """Build the tier response."""
    return TierOut(
        id=tier.id,
        creator_id=tier.creator_id,
        name=tier.name,
        price=tier.price,
        period=tier.period,
        # JSONField can hold anything; coerce defensively to list[str] so a
        # malformed row (e.g. a bare string) can't split into characters or 500.
        benefits=[str(b) for b in tier.benefits] if isinstance(tier.benefits, list) else [],
        badge=tier.badge,
        featured=tier.featured,
        sort_order=tier.sort_order,
    )


@tiers_router.get("", response=list[TierOut])
def list_tiers(
    request: HttpRequest, creator_id: uuid.UUID | None = None
) -> list[TierOut]:
    """List membership tiers, optionally filtered to one creator."""
    del request
    queryset = MembershipTier.objects.order_by("sort_order", "price")
    if creator_id is not None:
        queryset = queryset.filter(creator_id=creator_id)
    return [_tier_out(t) for t in queryset[:_MAX_TIERS]]


api.add_router("/tiers", tiers_router)
