"""Membership API — tier catalog (read) + mock subscriptions (SDLC 09 §4, B2·B4).

The tier catalog is read-only (returned whole — tiers per creator are a small
bounded set). B4 adds a fan subscription flow (``fan_auth``): subscribe to a tier
(**mock** — no money moves, B7 gated), list one's own subscriptions, and schedule
end-of-period cancellation. Filter the catalog to a creator via ``?creator_id=``.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import cast

from django.db import IntegrityError, transaction
from django.http import HttpRequest
from django.utils import timezone
from ninja import Router, Schema
from pydantic import Field

from apps.creator.models import Creator
from apps.identity.auth import fan_auth
from apps.identity.models import Account
from apps.membership.models import MembershipTier, Subscription, SubscriptionStatus
from config.api import api
from config.throttle import user_write_throttle

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
    """List *active* membership tiers, optionally filtered to one creator.

    Inactive tiers are owner-only (managed via ``/studio/tiers``) and excluded from
    this consumer surface, mirroring draft/hidden products in the catalog.
    """
    del request
    queryset = MembershipTier.objects.filter(active=True).order_by("sort_order", "price")
    if creator_id is not None:
        queryset = queryset.filter(creator_id=creator_id)
    return [_tier_out(t) for t in queryset[:_MAX_TIERS]]


api.add_router("/tiers", tiers_router)


class SubscriptionError(Schema):
    """Stable error shape for subscription and studio-tier endpoints."""

    detail: str


# --------------------------------------------------------------------------- #
# Studio (owner tier write; R3 — pure engineering, 법무 무관).
# Owner guard mirrors the commerce studio: only the account operating a Creator may
# manage that creator's tiers, scope is always that creator (never from the body),
# and the price is the creator's own display input (NOT a settlement figure).
# --------------------------------------------------------------------------- #
studio_tiers_router = Router(auth=fan_auth, tags=["studio-membership"])


class StudioTierOut(Schema):
    """Owner-view membership tier (adds the ``active`` management flag + timestamp)."""

    id: uuid.UUID
    creator_id: uuid.UUID | None = None
    name: str
    price: int
    period: str
    benefits: list[str]
    badge: str
    featured: bool
    active: bool
    sort_order: int
    created_at: datetime


class StudioTierIn(Schema):
    """Owner payload to create a membership tier (display price, not settlement)."""

    name: str = Field(min_length=1, max_length=40)
    price: int = Field(default=0, ge=0)
    period: str = Field(default="월", max_length=8)
    benefits: list[str] = Field(default_factory=list)
    badge: str = Field(default="", max_length=20)
    featured: bool = False
    active: bool = True
    sort_order: int = Field(default=0, ge=0)


class StudioTierPatch(Schema):
    """Owner payload to update a tier; only the provided fields are applied."""

    name: str | None = Field(default=None, min_length=1, max_length=40)
    price: int | None = Field(default=None, ge=0)
    period: str | None = Field(default=None, max_length=8)
    benefits: list[str] | None = None
    badge: str | None = Field(default=None, max_length=20)
    featured: bool | None = None
    active: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)


class StudioTierAck(Schema):
    """Bare status ack for studio mutations that return no body (delete)."""

    status: str


def _owner_creator(account: Account) -> Creator | None:
    """The creator profile operated by ``account`` (owner guard for studio writes)."""
    return Creator.objects.filter(owner=account).first()


def _studio_tier_out(tier: MembershipTier) -> StudioTierOut:
    """Build the owner-view tier response (includes the ``active`` flag)."""
    return StudioTierOut(
        id=tier.id,
        creator_id=tier.creator_id,
        name=tier.name,
        price=tier.price,
        period=tier.period,
        benefits=[str(b) for b in tier.benefits] if isinstance(tier.benefits, list) else [],
        badge=tier.badge,
        featured=tier.featured,
        active=tier.active,
        sort_order=tier.sort_order,
        created_at=tier.created_at,
    )


@studio_tiers_router.get("", response={200: list[StudioTierOut], 403: SubscriptionError})
def studio_list_tiers(
    request: HttpRequest,
) -> tuple[int, list[StudioTierOut] | SubscriptionError]:
    """List the caller's own creator's tiers, including inactive ones."""
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
    creator = _owner_creator(account)
    if creator is None:
        return 403, SubscriptionError(detail="크리에이터만 멤버십을 관리할 수 있어요.")
    tiers = MembershipTier.objects.filter(creator=creator).order_by("sort_order", "price")
    return 200, [_studio_tier_out(t) for t in tiers]


@studio_tiers_router.post(
    "",
    response={201: StudioTierOut, 403: SubscriptionError},
    throttle=user_write_throttle("30/min"),
)
def studio_create_tier(
    request: HttpRequest, payload: StudioTierIn
) -> tuple[int, StudioTierOut | SubscriptionError]:
    """Create a membership tier owned by the caller's creator; 403 if they operate none."""
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
    creator = _owner_creator(account)
    if creator is None:
        return 403, SubscriptionError(detail="크리에이터만 멤버십을 관리할 수 있어요.")
    tier = MembershipTier.objects.create(
        creator=creator,
        name=payload.name,
        price=payload.price,
        period=payload.period,
        benefits=payload.benefits,
        badge=payload.badge,
        featured=payload.featured,
        active=payload.active,
        sort_order=payload.sort_order,
    )
    return 201, _studio_tier_out(tier)


@studio_tiers_router.patch(
    "/{tier_id}",
    response={200: StudioTierOut, 403: SubscriptionError, 404: SubscriptionError},
    throttle=user_write_throttle("30/min"),
)
def studio_update_tier(
    request: HttpRequest, tier_id: uuid.UUID, payload: StudioTierPatch
) -> tuple[int, StudioTierOut | SubscriptionError]:
    """Update fields on the caller's own tier; 403 (no creator) / 404 (not theirs)."""
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
    creator = _owner_creator(account)
    if creator is None:
        return 403, SubscriptionError(detail="크리에이터만 멤버십을 관리할 수 있어요.")
    tier = MembershipTier.objects.filter(id=tier_id, creator=creator).first()
    if tier is None:
        return 404, SubscriptionError(detail="멤버십 등급을 찾을 수 없어요.")
    if payload.name is not None:
        tier.name = payload.name
    if payload.price is not None:
        tier.price = payload.price
    if payload.period is not None:
        tier.period = payload.period
    if payload.benefits is not None:
        tier.benefits = payload.benefits
    if payload.badge is not None:
        tier.badge = payload.badge
    if payload.featured is not None:
        tier.featured = payload.featured
    if payload.active is not None:
        tier.active = payload.active
    if payload.sort_order is not None:
        tier.sort_order = payload.sort_order
    tier.save()
    return 200, _studio_tier_out(tier)


@studio_tiers_router.delete(
    "/{tier_id}",
    response={
        200: StudioTierAck,
        403: SubscriptionError,
        404: SubscriptionError,
        422: SubscriptionError,
    },
    throttle=user_write_throttle("30/min"),
)
def studio_delete_tier(
    request: HttpRequest, tier_id: uuid.UUID
) -> tuple[int, StudioTierAck | SubscriptionError]:
    """Delete the caller's own tier; 403 (no creator) / 404 (not theirs) / 422 (in use).

    Deleting a tier CASCADEs its subscriptions (``Subscription.tier`` is CASCADE) —
    unlike a product delete, which SET_NULLs order lines to preserve history. To keep
    that asymmetry from silently destroying a live membership, a tier with any active
    subscription can't be deleted (422); the owner should set ``active=False`` (soft
    archive) to stop new signups while keeping existing subscriptions intact.
    """
    account = cast(Account, request.auth)  # type: ignore[attr-defined]
    creator = _owner_creator(account)
    if creator is None:
        return 403, SubscriptionError(detail="크리에이터만 멤버십을 관리할 수 있어요.")
    tier = MembershipTier.objects.filter(id=tier_id, creator=creator).first()
    if tier is None:
        return 404, SubscriptionError(detail="멤버십 등급을 찾을 수 없어요.")
    if Subscription.objects.filter(
        tier=tier, status=SubscriptionStatus.ACTIVE.value
    ).exists():
        return 422, SubscriptionError(
            detail="활성 구독이 있는 등급은 삭제할 수 없어요. 먼저 비활성화(active=False)하세요."
        )
    tier.delete()
    return 200, StudioTierAck(status="deleted")


api.add_router("/studio/tiers", studio_tiers_router)


# --------------------------------------------------------------------------- #
# Subscriptions (fan surface — mock payment, no money moves; B7 gated)
# --------------------------------------------------------------------------- #
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
    # Only an active (publicly listed) tier is subscribable; an inactive/archived or
    # unknown tier 404s (no existence leak), mirroring ``list_tiers``' active filter.
    tier = (
        MembershipTier.objects.select_related("creator")
        .filter(id=payload.tier_id, active=True)
        .first()
    )
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
