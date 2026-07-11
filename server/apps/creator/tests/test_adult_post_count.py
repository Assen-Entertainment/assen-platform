"""The public creator ``posts`` count applies the SAME 19+ gate as the post list.

Regression for ASS-296 #12: a creator's public post *count* did not apply the 19+
gate, so with adult content gated off the post LIST returned 0 while the COUNT
showed 1 — leaking the existence of hidden adult posts. The count must match the
gated list for a viewer who cannot see adult posts.
"""

from __future__ import annotations

import pytest
from django.test import Client, override_settings

from apps.content.models import Post
from apps.creator.models import Creator
from apps.identity.models import Account, KycStatus, Role
from apps.identity.services import issue_token_pair

pytestmark = pytest.mark.django_db


def _auth(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _verified_fan() -> Account:
    return Account.objects.create(
        role=Role.FAN.value, adult_verified=True, kyc_status=KycStatus.VERIFIED.value
    )


@override_settings(ENABLE_ADULT_CONTENT=False)
def test_adult_only_post_not_counted_when_flag_off(client: Client) -> None:
    """A creator whose only post is adult shows ``posts`` 0 to a non-verified viewer.

    The count matches the empty gated list (``?creator_id=`` returns nothing), so the
    hidden adult post's existence is not leaked through the profile count.
    """
    creator = Creator.objects.create(handle="stellar", name="별빛")
    Post.objects.create(creator=creator, body="성인 전용", adult_only=True)

    # Anonymous viewer: the public list is empty AND the profile count is 0.
    listed = client.get("/api/posts", data={"creator_id": str(creator.id)}).json()["items"]
    assert listed == []
    profile = client.get(f"/api/creators/{creator.handle}").json()
    assert profile["posts"] == 0

    # Even a verified fan sees no adult post (flag off hides it from everyone), so the
    # count stays 0 — matching the list.
    verified = _verified_fan()
    assert client.get(f"/api/creators/{creator.handle}", headers=_auth(verified)).json()[
        "posts"
    ] == 0


@override_settings(ENABLE_ADULT_CONTENT=True)
def test_adult_post_counted_only_for_verified_viewer(client: Client) -> None:
    """With the flag on, the adult post is counted only for an ``adult_verified`` viewer."""
    creator = Creator.objects.create(handle="stellar", name="별빛")
    Post.objects.create(creator=creator, body="성인 전용", adult_only=True)
    Post.objects.create(creator=creator, body="일반", adult_only=False)

    # Anonymous / unverified: only the normal post counts.
    assert client.get(f"/api/creators/{creator.handle}").json()["posts"] == 1
    unverified = Account.objects.create(role=Role.FAN.value)
    assert client.get(
        f"/api/creators/{creator.handle}", headers=_auth(unverified)
    ).json()["posts"] == 1

    # Verified: both posts count.
    verified = _verified_fan()
    assert client.get(
        f"/api/creators/{creator.handle}", headers=_auth(verified)
    ).json()["posts"] == 2
