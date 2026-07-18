"""Tests for the self-follow guard on the follow write API.

A creator must not be able to follow their OWN creator profile. Previously the
endpoint only suppressed the self-follow *notification* while still creating the
follow edge; it now rejects the follow outright (422 ``SelfFollowForbidden``)
before any edge is created. A normal fan following a different creator is
unaffected.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.creator.models import Creator
from apps.identity.models import Account, KycStatus, Role
from apps.identity.services import issue_token_pair
from apps.social.models import Follow
from config.errors import ErrorCode

pytestmark = pytest.mark.django_db


def _fan(nickname: str = "미오팬") -> Account:
    return Account.objects.create(
        role=Role.FAN.value, nickname=nickname, kyc_status=KycStatus.VERIFIED.value
    )


def _bearer(account: Account) -> dict[str, str]:
    """Authorization header carrying a freshly issued access token for ``account``."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _url(handle: str) -> str:
    return f"/api/creators/{handle}/follow"


def test_self_follow_is_rejected(client: Client) -> None:
    """A creator following their OWN handle is rejected (422), no edge created."""
    owner = _fan("본인")
    creator = Creator.objects.create(handle="selfown", name="본인크리", owner=owner)
    resp = client.put(_url(creator.handle), headers=_bearer(owner))
    assert resp.status_code == 422
    assert resp.json()["code"] == ErrorCode.SELF_FOLLOW_FORBIDDEN.value
    assert not Follow.objects.filter(follower=owner, creator=creator).exists()


def test_fan_can_follow_other_creator(client: Client) -> None:
    """A normal fan following a different creator still succeeds (200, edge created)."""
    owner = _fan("스텔라운영")
    creator = Creator.objects.create(handle="stellar", name="별빛", owner=owner)
    fan = _fan("다른팬")
    resp = client.put(_url(creator.handle), headers=_bearer(fan))
    assert resp.status_code == 200
    assert resp.json() == {"following": True, "followers": 1}
    assert Follow.objects.filter(follower=fan, creator=creator).exists()
