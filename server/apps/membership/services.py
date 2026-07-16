"""Membership entitlement — the server-authoritative "may this fan see/buy this?".

A paying fan's access to gated content and products is decided here, not by the
client. :func:`active_subscription` is the single membership predicate (mirroring
the ``uniq_active_subscription_per_creator`` constraint — one ACTIVE subscription
per (fan, creator)); :func:`can_view_post` layers post visibility on top of it.

Fail closed: an anonymous viewer never sees a ``members`` post, and a locked
product is never orderable without an active subscription (see
``apps.content.api`` / ``apps.commerce.api``).
"""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from apps.content.models import Post, PostVisibility
from apps.creator.models import Creator
from apps.identity.models import Account
from apps.membership.models import Subscription, SubscriptionStatus


def active_subscription(
    fan: Account | None, creator: Creator | None
) -> Subscription | None:
    """Return ``fan``'s truly-active subscription to ``creator`` (or ``None``).

    Mirrors the ``uniq_active_subscription_per_creator`` constraint: at most one
    ACTIVE subscription per (fan, creator), so ``first()`` is unambiguous. A missing
    fan or creator (e.g. a creatorless/global product) never has an entitlement, so
    it returns ``None`` rather than matching NULL creators.

    Billing state machine (#5): an ``expired`` (or ``cancelled``) status is excluded
    by the status filter. A *cancelled-but-still-active* sub (``cancelled_at`` set,
    "해지 예정") is entitled only until its ``current_period_end`` — this closes the
    window immediately at period end even if the billing worker has not yet run to
    flip the status. A renewing (non-cancelled) sub is always entitled; a free/legacy
    sub (no ``current_period_end``) is entitled while active.
    """
    if fan is None or creator is None:
        return None
    now = timezone.now()
    return (
        Subscription.objects.filter(
            fan=fan, creator=creator, status=SubscriptionStatus.ACTIVE.value
        )
        .filter(
            Q(cancelled_at__isnull=True)
            | Q(current_period_end__isnull=True)
            | Q(current_period_end__gt=now)
        )
        .first()
    )


def can_view_post(account: Account | None, post: Post) -> bool:
    """Whether ``account`` may read ``post``'s gated body/media.

    ``public`` posts are visible to everyone. A ``members`` post is visible only to
    a non-anonymous account that is (a) the post's own creator/owner, (b) an
    operator/staff account, or (c) an active subscriber of the creator whose tier
    matches ``required_tier`` when it is set (a NULL ``required_tier`` accepts any
    active subscription). Fail closed: anonymous → ``False`` for a ``members`` post.
    """
    if post.visibility == PostVisibility.PUBLIC.value:
        return True
    if account is None:
        return False
    creator = post.creator
    # (a) the post's own creator/owner always sees their own post.
    if creator.owner_id is not None and creator.owner_id == account.id:
        return True
    # (b) staff (operator/manager/admin/system) may view for moderation.
    if account.is_operator_account:
        return True
    # (c) an active subscriber whose tier matches the requirement.
    sub = active_subscription(account, creator)
    if sub is None:
        return False
    if post.required_tier_id is not None:
        return sub.tier_id == post.required_tier_id
    return True
