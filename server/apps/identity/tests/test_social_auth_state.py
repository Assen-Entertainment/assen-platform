"""Social login OAuth `state` binding: the signed httpOnly state cookie set at
``/social/{provider}/start`` must gate ``/callback`` so a callback forged by an
attacker (no cookie, mismatched state, or a swapped redirect_uri) cannot mint tokens
(Codex #7, login-CSRF / account-takeover). The Django test ``client`` persists
cookies across requests, so a real start→callback round-trip exercises the binding.
"""

from __future__ import annotations

import json

import pytest
from django.test import Client

from apps.identity.models import Account
from config.errors import ErrorCode


def _start_state(client: Client, provider: str, redirect_uri: str) -> str:
    """Begin the flow (setting the state cookie on ``client``) and return the state."""
    resp = client.get(
        f"/api/fan/social/{provider}/start", {"redirect_uri": redirect_uri}
    )
    assert resp.status_code == 200, resp.content
    return str(resp.json()["state"])


@pytest.mark.django_db
def test_callback_without_state_cookie_is_400(client: Client) -> None:
    # No /start was called on this client, so no state cookie is present.
    resp = client.post(
        "/api/fan/social/kakao/callback",
        data=json.dumps(
            {
                "code": "mock-kakao",
                "state": "forged",
                "redirect_uri": "http://web/cb",
                "consent_terms": True,
                "consent_privacy": True,
                "age_over_14": True,
                "web": True,
            }
        ),
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == ErrorCode.SOCIAL_UNAVAILABLE.value
    assert not Account.objects.filter(auth_method="kakao").exists()


@pytest.mark.django_db
def test_callback_with_mismatched_state_is_400(client: Client) -> None:
    _start_state(client, "kakao", "http://web/cb")
    resp = client.post(
        "/api/fan/social/kakao/callback",
        data=json.dumps(
            {
                "code": "mock-kakao",
                "state": "not-the-issued-state",
                "redirect_uri": "http://web/cb",
                "consent_terms": True,
                "consent_privacy": True,
                "age_over_14": True,
                "web": True,
            }
        ),
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == ErrorCode.SOCIAL_UNAVAILABLE.value
    assert not Account.objects.filter(auth_method="kakao").exists()


@pytest.mark.django_db
def test_callback_with_swapped_redirect_uri_is_400(client: Client) -> None:
    state = _start_state(client, "kakao", "http://web/cb")
    # Same (valid) state cookie, but a redirect_uri the flow did not start with.
    resp = client.post(
        "/api/fan/social/kakao/callback",
        data=json.dumps(
            {
                "code": "mock-kakao",
                "state": state,
                "redirect_uri": "http://evil/cb",
                "consent_terms": True,
                "consent_privacy": True,
                "age_over_14": True,
                "web": True,
            }
        ),
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == ErrorCode.SOCIAL_UNAVAILABLE.value
    assert not Account.objects.filter(auth_method="kakao").exists()


@pytest.mark.django_db
def test_callback_round_trip_succeeds_and_clears_state(client: Client) -> None:
    state = _start_state(client, "kakao", "http://web/cb")
    resp = client.post(
        "/api/fan/social/kakao/callback",
        data=json.dumps(
            {
                "code": "mock-kakao",
                "state": state,
                "redirect_uri": "http://web/cb",
                "consent_terms": True,
                "consent_privacy": True,
                "age_over_14": True,
                "web": True,
            }
        ),
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.content
    assert "assen_access" in resp.cookies
    # The single-use state cookie is consumed on success (cleared to an empty value).
    assert resp.cookies["assen_social_state"].value == ""
    assert Account.objects.filter(auth_method="kakao").exists()
