"""Acceptance tests for the consent gate and consent recording.

Covers: an account without the required consent is blocked from a business
command; after recording consent it passes; versioned re-consent is enforced;
recording rule consent emits the P0 event.
"""

from __future__ import annotations

import pytest

from apps.consent.gate import (
    ConsentRequired,
    assert_consent,
    has_consent,
    missing_consents,
    require_consent,
)
from apps.consent.models import ConsentKind
from apps.consent.services import record_consent
from apps.event_log.events import EventName
from apps.event_log.models import EventRecord
from apps.identity.models import Account, Role

pytestmark = pytest.mark.django_db


class _FakeRequest:
    """Minimal stand-in for an HttpRequest carrying an authenticated account."""

    def __init__(self, account: Account | None) -> None:
        self.account = account
        self.auth = account


def _fan() -> Account:
    """Create a fan account."""
    return Account.objects.create(role=Role.FAN.value)


def test_account_without_consent_is_blocked() -> None:
    """A command guarded by require_consent raises for an un-consented fan."""
    account = _fan()

    @require_consent(kind=ConsentKind.RULE.value)
    def create_reservation(request: _FakeRequest) -> str:
        return "ok"

    with pytest.raises(ConsentRequired):
        create_reservation(_FakeRequest(account))


def test_account_with_consent_passes_gate() -> None:
    """After recording consent, the same guarded command runs."""
    account = _fan()
    record_consent(account=account, kind=ConsentKind.RULE.value, version="1")

    @require_consent(kind=ConsentKind.RULE.value)
    def create_reservation(request: _FakeRequest) -> str:
        return "ok"

    assert create_reservation(_FakeRequest(account)) == "ok"


def test_versioned_consent_requires_exact_version() -> None:
    """Consent at v1 does not satisfy a gate that demands v2 (re-consent)."""
    account = _fan()
    record_consent(account=account, kind=ConsentKind.PRIVACY.value, version="1")

    assert has_consent(account, kind=ConsentKind.PRIVACY.value, version="1") is True
    assert has_consent(account, kind=ConsentKind.PRIVACY.value, version="2") is False

    with pytest.raises(ConsentRequired):
        assert_consent(account, kind=ConsentKind.PRIVACY.value, version="2")


def test_missing_consents_reports_all_outstanding() -> None:
    """A signup flow can list every still-needed consent at once."""
    account = _fan()
    record_consent(account=account, kind=ConsentKind.TERMS.value, version="1")

    outstanding = missing_consents(
        account,
        required=[
            (ConsentKind.TERMS.value, "1"),
            (ConsentKind.PRIVACY.value, "1"),
            (ConsentKind.RULE.value, "1"),
        ],
    )
    assert (ConsentKind.TERMS.value, "1") not in outstanding
    assert (ConsentKind.PRIVACY.value, "1") in outstanding
    assert (ConsentKind.RULE.value, "1") in outstanding


def test_recording_rule_consent_emits_event() -> None:
    """Granting rule consent writes the P0 rule_consent_given event."""
    account = _fan()
    record_consent(account=account, kind=ConsentKind.RULE.value, version="3")

    event = EventRecord.objects.get(event_name=EventName.RULE_CONSENT_GIVEN.value)
    assert event.payload["consent_version"] == "3"
    assert event.fan_id == str(account.fan_id)


def test_request_without_account_is_blocked() -> None:
    """A guarded command with no authenticated account raises (defensive)."""

    @require_consent(kind=ConsentKind.RULE.value)
    def cmd(request: _FakeRequest) -> str:
        return "ok"

    with pytest.raises(ConsentRequired):
        cmd(_FakeRequest(None))
