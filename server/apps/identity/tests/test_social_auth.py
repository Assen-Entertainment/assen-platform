"""Social login: config.social_auth seam + social_services + /api/fan/social/* API."""

from __future__ import annotations

import json

import pytest
from django.test import Client
from pytest_django.fixtures import SettingsWrapper

from apps.identity.models import Account, Role
from apps.identity.signup_services import SignupError
from apps.identity.social_services import hash_social, register_or_login_social
from config.errors import ErrorCode
from config.social_auth import (
    MockSocialAuthProvider,
    SocialProfile,
    social_auth_provider,
)


def test_provider_gated_on_flag(settings: SettingsWrapper) -> None:
    settings.ENABLE_MOCK_SOCIAL_AUTH = True
    assert isinstance(social_auth_provider(), MockSocialAuthProvider)
    settings.ENABLE_MOCK_SOCIAL_AUTH = False
    assert social_auth_provider() is None


def test_mock_authorize_url_bounces_back_with_code() -> None:
    url = MockSocialAuthProvider().authorize_url(
        provider="kakao", state="st", redirect_uri="http://web/auth/callback"
    )
    assert url.startswith("http://web/auth/callback?")
    assert "code=mock-kakao" in url
    assert "state=st" in url


def test_mock_exchange_returns_stable_profile() -> None:
    profile = MockSocialAuthProvider().exchange(
        provider="kakao", code="mock-kakao", redirect_uri="http://web/cb"
    )
    assert isinstance(profile, SocialProfile)
    assert profile.provider == "kakao"
    assert profile.subject == "mock-kakao-user"


def test_hash_social_namespaced_and_deterministic() -> None:
    key = hash_social("kakao", "u1")
    assert key.startswith("s1:")
    assert key == hash_social("kakao", "u1")  # deterministic
    assert key != hash_social("google", "u1")  # provider-scoped
    assert key != hash_social("kakao", "u2")  # subject-scoped


@pytest.mark.django_db
def test_register_social_new_requires_consent() -> None:
    with pytest.raises(SignupError) as exc:
        register_or_login_social(provider="kakao", subject="u1", display_name="X")
    assert exc.value.code == ErrorCode.CONSENT_REQUIRED
    # the get_or_create insert rolled back — no consent-less account persists
    assert not Account.objects.filter(
        auth_subject_hash=hash_social("kakao", "u1")
    ).exists()


@pytest.mark.django_db
def test_register_social_creates_then_reuses() -> None:
    pair = register_or_login_social(
        provider="kakao",
        subject="u1",
        display_name="카카오유저",
        consent_terms=True,
        consent_privacy=True,
        age_over_14=True,
    )
    assert pair.access_token
    account = Account.objects.get(auth_subject_hash=hash_social("kakao", "u1"))
    assert account.role == Role.FAN.value
    assert account.auth_method == "kakao"
    # a returning identity reuses the SAME account (no duplicate, no consent needed)
    register_or_login_social(provider="kakao", subject="u1", display_name="카카오유저")
    assert (
        Account.objects.filter(auth_subject_hash=hash_social("kakao", "u1")).count()
        == 1
    )


@pytest.mark.django_db
def test_start_endpoint_returns_authorize_url(client: Client) -> None:
    resp = client.get(
        "/api/fan/social/kakao/start",
        {"redirect_uri": "http://web/auth/callback"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "code=mock-kakao" in body["authorize_url"]
    assert body["state"]


@pytest.mark.django_db
def test_start_endpoint_rejects_unknown_provider(client: Client) -> None:
    resp = client.get(
        "/api/fan/social/nope/start", {"redirect_uri": "http://web/cb"}
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == ErrorCode.SOCIAL_PROVIDER_UNSUPPORTED.value


@pytest.mark.django_db
def test_callback_signs_up_and_sets_cookie(client: Client) -> None:
    resp = client.post(
        "/api/fan/social/kakao/callback",
        data=json.dumps(
            {
                "code": "mock-kakao",
                "state": "st",
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
    assert Account.objects.filter(auth_method="kakao").exists()


@pytest.mark.django_db
def test_callback_new_without_consent_is_422(client: Client) -> None:
    resp = client.post(
        "/api/fan/social/google/callback",
        data=json.dumps(
            {"code": "mock-google", "redirect_uri": "http://web/cb", "web": True}
        ),
        content_type="application/json",
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == ErrorCode.CONSENT_REQUIRED.value
