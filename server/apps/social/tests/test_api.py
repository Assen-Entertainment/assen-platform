"""Tests for the follow / unfollow write API (E11/B4).

Covers idempotent follow/unfollow with fresh follower counts, the unauthenticated
401 gate, the cookie-surface CSRF 403 path, and the unknown-handle 404. The read
side (the per-user ``following`` flag) is asserted in the creator API tests.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client

from apps.creator.models import Creator
from apps.identity.cookies import ACCESS_COOKIE_NAME
from apps.identity.models import Account, KycStatus, Role
from apps.identity.services import issue_token_pair
from apps.social.models import Follow

pytestmark = pytest.mark.django_db


def _creator(handle: str = "stellar") -> Creator:
    return Creator.objects.create(handle=handle, name="별빛", verified=True)


def _fan(nickname: str = "미오팬") -> Account:
    return Account.objects.create(
        role=Role.FAN.value, nickname=nickname, kyc_status=KycStatus.VERIFIED.value
    )


def _bearer(account: Account) -> dict[str, str]:
    """Authorization header carrying a freshly issued access token for ``account``."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _url(handle: str) -> str:
    return f"/api/creators/{handle}/follow"


def _json(resp: Any) -> Any:
    return resp.json()


def test_follow_creates_edge_and_returns_count(client: Client) -> None:
    """PUT follows the creator and reports the new aggregate follower count."""
    creator = _creator()
    fan = _fan()
    resp = client.put(_url(creator.handle), headers=_bearer(fan))
    assert resp.status_code == 200
    assert _json(resp) == {"following": True, "followers": 1}
    assert Follow.objects.filter(follower=fan, creator=creator).exists()


def test_follow_is_idempotent(client: Client) -> None:
    """A second PUT is a no-op (still 200, count stays 1, one edge)."""
    creator = _creator()
    fan = _fan()
    headers = _bearer(fan)
    first = client.put(_url(creator.handle), headers=headers)
    second = client.put(_url(creator.handle), headers=headers)
    assert first.status_code == second.status_code == 200
    assert _json(second) == {"following": True, "followers": 1}
    assert Follow.objects.filter(follower=fan, creator=creator).count() == 1


def test_unfollow_removes_edge_and_is_idempotent(client: Client) -> None:
    """DELETE removes the edge; unfollowing when not following is still 200."""
    creator = _creator()
    fan = _fan()
    headers = _bearer(fan)
    client.put(_url(creator.handle), headers=headers)

    gone = client.delete(_url(creator.handle), headers=headers)
    assert gone.status_code == 200
    assert _json(gone) == {"following": False, "followers": 0}
    assert not Follow.objects.filter(follower=fan, creator=creator).exists()

    again = client.delete(_url(creator.handle), headers=headers)
    assert again.status_code == 200
    assert _json(again) == {"following": False, "followers": 0}


def test_follow_requires_auth(client: Client) -> None:
    """An unauthenticated follow is rejected (401), no edge created."""
    creator = _creator()
    resp = client.put(_url(creator.handle))
    assert resp.status_code in {401, 403}
    assert Follow.objects.count() == 0


def test_follow_unknown_handle_is_404(client: Client) -> None:
    """Following an unknown handle returns 404 with the stable error shape."""
    resp = client.put(_url("nobody"), headers=_bearer(_fan()))
    assert resp.status_code == 404
    assert _json(resp) == {"detail": "creator not found"}


def test_cookie_surface_follow_without_csrf_is_403() -> None:
    """The web (cookie) surface enforces CSRF: an unsafe write with no token is 403.

    The bearer surface is CSRF-free (all other tests use it); this asserts the
    cookie double-submit gate blocks a forged cross-site write.
    """
    csrf_client = Client(enforce_csrf_checks=True)
    creator = _creator()
    fan = _fan()
    csrf_client.cookies[ACCESS_COOKIE_NAME] = issue_token_pair(fan).access_token
    resp = csrf_client.put(_url(creator.handle))
    assert resp.status_code == 403
    assert Follow.objects.count() == 0


def test_follow_notifies_creator_owner(client: Client) -> None:
    """A fresh follow appends a follow notification to the creator owner's feed."""
    from apps.notification.models import Notification

    owner = _fan("스텔라운영")
    creator = Creator.objects.create(handle="owned", name="별빛", owner=owner)
    fan = _fan("알림팬")
    resp = client.put(_url(creator.handle), headers=_bearer(fan))
    assert resp.status_code == 200
    row = Notification.objects.filter(recipient=owner, kind="follow").first()
    assert row is not None
    assert row.href == f"/creator/{creator.handle}"

    # 멱등 재팔로우는 알림을 중복 생성하지 않는다.
    client.put(_url(creator.handle), headers=_bearer(fan))
    assert Notification.objects.filter(recipient=owner, kind="follow").count() == 1


def test_self_follow_does_not_notify(client: Client) -> None:
    """A creator following their own page is rejected (422) and never self-notifies.

    The self-follow guard now rejects the follow before any edge is created (see
    tests/test_self_follow.py), so the self-notification path is unreachable — this
    still asserts that a creator can never notify themselves via their own follow.
    """
    from apps.notification.models import Notification

    owner = _fan("본인")
    creator = Creator.objects.create(handle="selfown", name="본인크리", owner=owner)
    resp = client.put(_url(creator.handle), headers=_bearer(owner))
    assert resp.status_code == 422
    assert not Notification.objects.filter(recipient=owner, kind="follow").exists()
