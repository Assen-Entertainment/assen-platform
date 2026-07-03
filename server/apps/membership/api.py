"""Membership API — tier catalog (read) + mock subscriptions (SDLC 09 §4, B2·B4).

The tier catalog is read-only (returned whole — tiers per creator are a small
bounded set). B4 adds a fan subscription flow (``fan_auth``): subscribe to a tier
(**mock** — no money moves, B7 gated), list one's own subscriptions, and schedule
end-of-period cancellation. Filter the catalog to a creator via ``?creator_id=``.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import cast

from django.db import IntegrityError, transaction
from django.http import HttpRequest
from django.utils import timezone
from ninja import Router, Schema

from apps.identity.auth import fan_auth
from apps.identity.models import Account
from apps.membership.models import MembershipTier, Subscription, SubscriptionStatus
from config.api import api

# Mock billing cycle length; there is no real recurring billing (B7 gated).
_BILLING_CYCLE = timedelta(days=30)

tiers_router = Router(tags=["membership"])
subscriptions_router = Router(auth=fan_auth, tags=["membership-subscriptions"])

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


# --------------------------------------------------------------------------- #
# Subscriptions (fan surface — mock payment, no money moves; B7 gated)
# --------------------------------------------------------------------------- #
class SubscriptionError(Schema):
    """Stable error shape for subscription endpoints."""

    detail: str


class SubscriptionOut(Schema):
    """A fan's subscription (maps to the frontend ``Subscription`` type).

    ``cancel_scheduled`` is ``True`` for an active subscription the fan has set to
    end at period-end ("해지 예정"); the web renders that state distinctly.
    """

    id: uuid.UUID
    creator_id: uuid.UUID | None = None
    creator_name: str
    creator_handle: str
    tier_id: uuid.UUID | None = None
    tier_name: str
    price: int
    period: str
    status: str
    next_billing_date: date
    cancel_scheduled: bool


class SubscribeIn(Schema):
    """Fan payload to subscribe to a membership tier."""

    tier_id: uuid.UUID


def _subscription_out(sub: Subscription) -> SubscriptionOut:
    """Build the subscription response from a subscription with tier/creator loaded."""
    tier = sub.tier
    creator = tier.creator
    return SubscriptionOut(
        id=sub.id,
        creator_id=creator.id if creator is not None else None,
        creator_name=creator.name if creator is not None else "",
        creator_handle=creator.handle if creator is not None else "",
        tier_id=tier.id,
        tier_name=tier.name,
        price=tier.price,
        period=tier.period,
        status=sub.status,
        next_billing_date=sub.next_billing_date,
        cancel_scheduled=(
            sub.status == SubscriptionStatus.ACTIVE.value and sub.cancelled_at is not None
        ),
    )


@subscriptions_router.post(
    "", response={201: SubscriptionOut, 404: SubscriptionError, 422: SubscriptionError}
)
def subscribe(
    request: HttpRequest, payload: SubscribeIn
) -> tuple[int, SubscriptionOut | SubscriptionError]:
    """Subscribe the requesting fan to a tier (mock — no money moves).

    Refuses (422) if the fan already has an active subscription to the same
    creator (one active membership per creator).
    """
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
    tier = MembershipTier.objects.select_related("creator").filter(id=payload.tier_id).first()
    if tier is None:
        return 404, SubscriptionError(detail="멤버십 등급을 찾을 수 없어요.")
    active = Subscription.objects.filter(fan=account, status=SubscriptionStatus.ACTIVE)
    # Dedup by creator when the tier belongs to one; otherwise by the exact tier.
    if tier.creator is not None:
        active = active.filter(tier__creator=tier.creator)
    else:
        active = active.filter(tier=tier)
    if active.exists():
        return 422, SubscriptionError(detail="이미 구독 중인 크리에이터예요.")
    # The exists() check above is the fast path; the (fan, creator) partial-unique
    # constraint is the race-safe backstop (B2). Two concurrent subscribes can both
    # pass the check — the DB rejects the second insert, which we surface as 422.
    try:
        with transaction.atomic():
            sub = Subscription.objects.create(
                fan=account,
                tier=tier,
                status=SubscriptionStatus.ACTIVE,
                next_billing_date=timezone.localdate() + _BILLING_CYCLE,
            )
    except IntegrityError:
        return 422, SubscriptionError(detail="이미 구독 중인 크리에이터예요.")
    return 201, _subscription_out(sub)


@subscriptions_router.get("", response=list[SubscriptionOut])
def list_subscriptions(request: HttpRequest) -> list[SubscriptionOut]:
    """List the requesting fan's own subscriptions (newest first)."""
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
    subs = (
        Subscription.objects.filter(fan=account)
        .select_related("tier", "tier__creator")
        .order_by("-started_at")
    )
    return [_subscription_out(s) for s in subs]


@subscriptions_router.post(
    "/{subscription_id}/cancel",
    response={200: SubscriptionOut, 404: SubscriptionError, 422: SubscriptionError},
)
def cancel_subscription(
    request: HttpRequest, subscription_id: uuid.UUID
) -> tuple[int, SubscriptionOut | SubscriptionError]:
    """Schedule end-of-period cancellation of the fan's own subscription.

    "말일 해지": records ``cancelled_at`` and keeps ``status = active`` so the
    membership stays usable until period-end; the response's ``cancel_scheduled``
    flag lets the web show "해지 예정". A real billing job would flip it later.
    """
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
    sub = (
        Subscription.objects.select_related("tier", "tier__creator")
        .filter(id=subscription_id, fan=account)
        .first()
    )
    if sub is None:
        return 404, SubscriptionError(detail="구독을 찾을 수 없어요.")
    if sub.status != SubscriptionStatus.ACTIVE.value or sub.cancelled_at is not None:
        return 422, SubscriptionError(detail="이미 해지 예정이거나 해지된 구독이에요.")
    sub.cancelled_at = timezone.now()
    sub.save(update_fields=["cancelled_at"])
    return 200, _subscription_out(sub)


api.add_router("/subscriptions", subscriptions_router)
