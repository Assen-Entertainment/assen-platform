"""API tests for cast endpoints (ASS-92) — the three-tier access + fan gate.

These prove the access rules: operators manage content, only managers grant the
portrait-rights consent, and a fan sees a profile only once it is published *and*
name-consented — with a hidden profile 404ing and a fan view recording an
impression.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.cast.models import ConsentScope, ConsentStatus, ProfileVisibility
from apps.event_log.events import EventName
from apps.event_log.models import EventRecord
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair

pytestmark = pytest.mark.django_db

_STAGE_NAME = "사쿠라"


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _auth(account: Account) -> dict[str, str]:
    """Return a test-client ``headers`` mapping with an issued bearer token."""
    token = issue_token_pair(account).access_token
    return {"authorization": f"Bearer {token}"}


def _create_profile(client: Client, operator: Account) -> str:
    """Create a profile via the API and return its cast_id."""
    response = client.post(
        "/api/cast/profiles",
        data={"stage_name": _STAGE_NAME},
        content_type="application/json",
        headers=_auth(operator),
    )
    assert response.status_code == 201
    cast_id: str = response.json()["cast_id"]
    return cast_id


def test_operator_creates_profile_private_and_hidden(client: Client) -> None:
    """An operator creates a profile; it is private with all scopes withheld."""
    operator = _account(Role.OPERATOR.value)

    response = client.post(
        "/api/cast/profiles",
        data={"stage_name": _STAGE_NAME, "cheki_available": True},
        content_type="application/json",
        headers=_auth(operator),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["visibility"] == ProfileVisibility.PRIVATE.value
    assert body["cheki_available"] is True
    assert body["consents"][ConsentScope.STAGE_NAME.value] == ConsentStatus.WITHHELD.value


def test_create_requires_staff(client: Client) -> None:
    """A fan or an anonymous caller cannot create a profile."""
    fan = _account(Role.FAN.value)
    fan_resp = client.post(
        "/api/cast/profiles",
        data={"stage_name": _STAGE_NAME},
        content_type="application/json",
        headers=_auth(fan),
    )
    assert fan_resp.status_code in {401, 403}

    anon_resp = client.post(
        "/api/cast/profiles",
        data={"stage_name": _STAGE_NAME},
        content_type="application/json",
    )
    assert anon_resp.status_code in {401, 403}


def test_operator_lists_and_reads_profile(client: Client) -> None:
    """An operator lists and reads a profile with its consent map."""
    operator = _account(Role.OPERATOR.value)
    cast_id = _create_profile(client, operator)

    listed = client.get("/api/cast/profiles", headers=_auth(operator))
    assert listed.status_code == 200
    assert any(row["cast_id"] == cast_id for row in listed.json())

    got = client.get(f"/api/cast/profiles/{cast_id}", headers=_auth(operator))
    assert got.status_code == 200
    assert got.json()["stage_name"] == _STAGE_NAME


def test_operator_updates_visibility(client: Client) -> None:
    """An operator can toggle the publish control."""
    operator = _account(Role.OPERATOR.value)
    cast_id = _create_profile(client, operator)

    patched = client.patch(
        f"/api/cast/profiles/{cast_id}",
        data={"visibility": ProfileVisibility.PUBLIC.value},
        content_type="application/json",
        headers=_auth(operator),
    )
    assert patched.status_code == 200
    assert patched.json()["visibility"] == ProfileVisibility.PUBLIC.value


def test_update_rejects_unknown_visibility(client: Client) -> None:
    """An unknown visibility value is a 422, not a silent no-op."""
    operator = _account(Role.OPERATOR.value)
    cast_id = _create_profile(client, operator)

    patched = client.patch(
        f"/api/cast/profiles/{cast_id}",
        data={"visibility": "everyone"},
        content_type="application/json",
        headers=_auth(operator),
    )
    assert patched.status_code == 422


def test_consent_requires_manager(client: Client) -> None:
    """Recording consent is manager+; an operator is refused the rights gate."""
    operator = _account(Role.OPERATOR.value)
    cast_id = _create_profile(client, operator)

    op_resp = client.post(
        f"/api/cast/profiles/{cast_id}/consent",
        data={"scope": ConsentScope.STAGE_NAME.value, "status": ConsentStatus.GRANTED.value},
        content_type="application/json",
        headers=_auth(operator),
    )
    assert op_resp.status_code in {401, 403}


def test_manager_records_consent(client: Client) -> None:
    """A manager records a scope's consent and it shows in the operator view."""
    operator = _account(Role.OPERATOR.value)
    manager = _account(Role.MANAGER.value)
    cast_id = _create_profile(client, operator)

    response = client.post(
        f"/api/cast/profiles/{cast_id}/consent",
        data={"scope": ConsentScope.STAGE_NAME.value, "status": ConsentStatus.GRANTED.value},
        content_type="application/json",
        headers=_auth(manager),
    )
    assert response.status_code == 200
    consents = response.json()["consents"]
    assert consents[ConsentScope.STAGE_NAME.value] == ConsentStatus.GRANTED.value


def test_fan_sees_profile_only_after_publish_and_consent(client: Client) -> None:
    """The fan view is fail-closed: 404 until published + name-consented, then 200."""
    operator = _account(Role.OPERATOR.value)
    manager = _account(Role.MANAGER.value)
    fan = _account(Role.FAN.value)
    cast_id = _create_profile(client, operator)

    # Hidden by default.
    hidden = client.get(f"/api/cast/public-profiles/{cast_id}", headers=_auth(fan))
    assert hidden.status_code == 404

    # Publish + grant the name scope.
    client.patch(
        f"/api/cast/profiles/{cast_id}",
        data={"visibility": ProfileVisibility.PUBLIC.value},
        content_type="application/json",
        headers=_auth(operator),
    )
    client.post(
        f"/api/cast/profiles/{cast_id}/consent",
        data={"scope": ConsentScope.STAGE_NAME.value, "status": ConsentStatus.GRANTED.value},
        content_type="application/json",
        headers=_auth(manager),
    )

    shown = client.get(f"/api/cast/public-profiles/{cast_id}", headers=_auth(fan))
    assert shown.status_code == 200
    body = shown.json()
    assert body["stage_name"] == _STAGE_NAME
    # Photo not consented → withheld even though the profile is visible.
    assert body["photo_ref"] == ""
    # The view recorded an impression.
    assert EventRecord.objects.filter(
        event_name=EventName.CAST_PROFILE_VIEWED.value, cast_id=cast_id
    ).exists()


def test_fan_endpoint_rejects_staff_token(client: Client) -> None:
    """A staff token must not be logged as a fan impression (role gate)."""
    operator = _account(Role.OPERATOR.value)
    cast_id = _create_profile(client, operator)
    # Make it visible so only the role gate can refuse the staff caller.
    client.patch(
        f"/api/cast/profiles/{cast_id}",
        data={"visibility": ProfileVisibility.PUBLIC.value},
        content_type="application/json",
        headers=_auth(operator),
    )
    manager = _account(Role.MANAGER.value)
    client.post(
        f"/api/cast/profiles/{cast_id}/consent",
        data={"scope": ConsentScope.STAGE_NAME.value, "status": ConsentStatus.GRANTED.value},
        content_type="application/json",
        headers=_auth(manager),
    )

    staff_resp = client.get(f"/api/cast/public-profiles/{cast_id}", headers=_auth(operator))
    assert staff_resp.status_code == 403


def test_fan_endpoint_requires_authentication(client: Client) -> None:
    """An anonymous caller cannot read the fan view."""
    operator = _account(Role.OPERATOR.value)
    cast_id = _create_profile(client, operator)
    anon = client.get(f"/api/cast/public-profiles/{cast_id}")
    assert anon.status_code in {401, 403}
