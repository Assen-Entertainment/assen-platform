"""Social login → fan account (the OAuth counterpart of ``register_fan``).

Turns a verified :class:`~config.social_auth.SocialProfile` (provider + opaque
subject) into a fan :class:`~apps.identity.models.Account` and a token pair via the
**unchanged** token core. The account is keyed on a namespaced HMAC of
``provider:subject`` (:func:`hash_social`), reusing ``Account.auth_subject_hash`` so
no new model / migration is needed; account *linking* across auth methods (phone ↔
social) is a later feature — a first social login mints its own fan account.

Privacy: only the derived ``s1:`` hash + the display nickname persist; the raw
provider subject/token is never stored. On first login the terms/privacy consent and
the 만 14세 이상 floor are mandatory (same as phone signup, Fan_Signup_Privacy_Policy
§5); a returning social login skips consent and just re-issues tokens.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone

from apps.consent.models import ConsentKind
from apps.consent.services import record_consent
from apps.consent.versions import consent_doc_version
from apps.event_log.events import ActorType, EventName, EventSource
from apps.event_log.services import emit_event
from apps.identity.models import Account, Role
from apps.identity.services import IssuedTokenPair, issue_token_pair
from apps.identity.signup_services import (
    SignupError,
    _phone_hmac_key,
)
from config.errors import ErrorCode


def hash_social(provider: str, subject: str) -> str:
    """Namespaced account key for a social identity — keyed HMAC, ``s1:`` prefixed.

    A distinct ``s1:`` prefix (vs the phone ``v1:``) guarantees a social subject can
    never collide with a phone hash. Reuses the dedicated identifier HMAC key
    (``PHONE_IDENTIFIER_HMAC_KEY``) so a stolen DB alone cannot enumerate provider
    subjects — the same defence phone hashing gets (ASS-287 A-2).
    """
    msg = f"social:{provider}:{subject}".encode()
    mac = hmac.new(_phone_hmac_key(), msg, hashlib.sha256).digest()
    return "s1:" + base64.urlsafe_b64encode(mac).rstrip(b"=").decode("ascii")


_SOCIAL_STATE_SALT = "assen.social.state"


def make_social_state(*, provider: str, redirect_uri: str) -> tuple[str, str]:
    """Return (echoed_state, signed_cookie). echoed_state goes to the provider in the
    authorize URL; signed_cookie is stored httpOnly and re-verified on callback so the
    callback is bound to the browser+provider+redirect_uri that started the flow."""
    state = secrets.token_urlsafe(24)
    signed = signing.dumps({"s": state, "p": provider, "r": redirect_uri}, salt=_SOCIAL_STATE_SALT)
    return state, signed


def verify_social_state(
    *, cookie_value: str | None, provider: str, redirect_uri: str, echoed_state: str
) -> bool:
    if not cookie_value:
        return False
    try:
        payload = signing.loads(
            cookie_value, salt=_SOCIAL_STATE_SALT, max_age=settings.SOCIAL_STATE_TTL_SECONDS
        )
    except signing.BadSignature:
        return False
    return (
        isinstance(payload, dict)
        and payload.get("s") == echoed_state
        and payload.get("p") == provider
        and payload.get("r") == redirect_uri
    )


@transaction.atomic
def register_or_login_social(
    *,
    provider: str,
    subject: str,
    display_name: str | None,
    consent_terms: bool = False,
    consent_privacy: bool = False,
    age_over_14: bool = False,
) -> IssuedTokenPair:
    """Log in (or, on first sight, register) a fan from a verified social identity.

    A returning social identity reuses its account and just gets a fresh token pair.
    A first-time identity requires terms/privacy consent + the 만 14세 이상 floor (the
    same mandatory consent as phone signup — the whole insert rolls back if either is
    missing) and emits ``fan_signed_up`` exactly once.
    """
    subject_hash = hash_social(provider, subject)
    nickname = (display_name or "회원").strip()[:40] or "회원"
    account, created = Account.objects.get_or_create(
        auth_subject_hash=subject_hash,
        role=Role.FAN.value,
        defaults={"nickname": nickname, "auth_method": provider},
    )
    if created:
        # Mandatory consent for a NEW fan (Fan_Signup_Privacy_Policy §5 / D5). Raising
        # rolls back the get_or_create insert (this whole function is atomic), so no
        # consent-less account is ever persisted; the client re-submits with consent.
        if not (consent_terms and consent_privacy):
            raise SignupError(
                "Both terms and privacy consent are required.",
                code=ErrorCode.CONSENT_REQUIRED,
            )
        if not age_over_14:
            raise SignupError(
                "만 14세 이상만 가입할 수 있습니다.", code=ErrorCode.UNDERAGE
            )
        # Stamp the presented document version per document from the server consent
        # version registry (apps.consent.versions — 법무-게이트: placeholder values),
        # so a first social signup records WHICH policy text was agreed to.
        record_consent(
            account=account,
            kind=ConsentKind.TERMS.value,
            version=consent_doc_version(ConsentKind.TERMS.value),
        )
        record_consent(
            account=account,
            kind=ConsentKind.PRIVACY.value,
            version=consent_doc_version(ConsentKind.PRIVACY.value),
        )
        emit_event(
            event_name=EventName.FAN_SIGNED_UP.value,
            occurred_at=timezone.now(),
            actor_type=ActorType.FAN.value,
            source=EventSource.WEB.value,
            fan_id=str(account.fan_id),
            payload={
                "fan_id": str(account.fan_id),
                # signup *channel* (Data_Event_Schema domain qr/web/admin/import); the
                # social provider itself lives on Account.auth_method.
                "signup_method": "web",
                "consent_terms": consent_terms,
                "consent_privacy": consent_privacy,
            },
        )
    return issue_token_pair(account)
