"""Real OAuth adapters (카카오/Google/Naver) in config.social_auth.

Kept separate from test_social_auth.py (the seam/mock/API tests) so the real-adapter
coverage is a NEW file — HTTP is monkeypatched, no live provider call is made.
"""

from __future__ import annotations

import pytest

from config import social_auth as sa


def test_real_authorize_url_builds_provider_consent_url():
    provider = sa.RealSocialAuthProvider({"kakao": ("KID", "KSEC")})
    url = provider.authorize_url(
        provider="kakao", state="st", redirect_uri="https://app/cb"
    )
    assert url.startswith("https://kauth.kakao.com/oauth/authorize?")
    assert "client_id=KID" in url
    assert "response_type=code" in url
    assert "state=st" in url
    assert "scope=profile_nickname" in url


def test_real_falls_back_to_mock_for_unconfigured_provider():
    provider = sa.RealSocialAuthProvider(
        {"kakao": ("KID", "KSEC")}, fallback=sa.MockSocialAuthProvider()
    )
    url = provider.authorize_url(
        provider="google", state="s", redirect_uri="https://app/cb"
    )
    assert "code=mock-google" in url  # google unconfigured → mock bounce


def test_real_raises_for_unconfigured_provider_without_fallback():
    provider = sa.RealSocialAuthProvider({"kakao": ("KID", "KSEC")})
    with pytest.raises(sa.SocialAuthError):
        provider.authorize_url(
            provider="naver", state="s", redirect_uri="https://app/cb"
        )


@pytest.mark.parametrize(
    "provider, userinfo, subject, name",
    [
        (
            "kakao",
            {"id": 12345, "kakao_account": {"profile": {"nickname": "카카오짱"}}},
            "12345",
            "카카오짱",
        ),
        ("google", {"sub": "g-987", "name": "구글러"}, "g-987", "구글러"),
        ("naver", {"response": {"id": "n-1", "nickname": "네이버님"}}, "n-1", "네이버님"),
    ],
)
def test_real_exchange_maps_profile(monkeypatch, provider, userinfo, subject, name):
    monkeypatch.setattr(sa, "_post_form", lambda url, data: {"access_token": "tok"})
    monkeypatch.setattr(sa, "_get_json", lambda url, headers: userinfo)
    prof = sa.RealSocialAuthProvider({provider: ("id", "sec")}).exchange(
        provider=provider, code="c", redirect_uri="https://app/cb"
    )
    assert prof.provider == provider
    assert prof.subject == subject
    assert prof.display_name == name


def test_real_exchange_raises_without_token(monkeypatch):
    monkeypatch.setattr(sa, "_post_form", lambda url, data: {})
    with pytest.raises(sa.SocialAuthError):
        sa.RealSocialAuthProvider({"kakao": ("id", "sec")}).exchange(
            provider="kakao", code="c", redirect_uri="https://app/cb"
        )


def test_accessor_prefers_real_and_mocks_the_rest(settings):
    settings.ENABLE_MOCK_SOCIAL_AUTH = True
    settings.SOCIAL_KAKAO_CLIENT_ID = "KID"
    settings.SOCIAL_KAKAO_CLIENT_SECRET = "KSEC"
    provider = sa.social_auth_provider()
    assert isinstance(provider, sa.RealSocialAuthProvider)
    assert "kauth.kakao.com" in provider.authorize_url(
        provider="kakao", state="s", redirect_uri="https://app/cb"
    )
    assert "code=mock-google" in provider.authorize_url(
        provider="google", state="s", redirect_uri="https://app/cb"
    )
