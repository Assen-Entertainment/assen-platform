"""Tests for the visit-guide API (F02, ASS-101 v0).

Covers the operator surface (create/list/detail/update/publish/unpublish), the
public surface (published-only list/detail, draft 404, no-auth read), the fan
rule acknowledgement, and the gates (operator role, fan role, anonymous).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.test import Client

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair

pytestmark = pytest.mark.django_db

OP = "/api/operator/visit-guide"
PUB = "/api/visit-guide"
FAN = "/api/fan/visit-guide"
JSON = "application/json"
RULES = "usage_rules"
GUIDE = "first_visit_guide"


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _auth(account: Account) -> dict[str, str]:
    """Return a Django test-client ``headers`` mapping for an issued token."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _create(client: Client, op: Account, **over: object) -> Any:
    """Create a draft section via the operator API and return the body."""
    data: dict[str, object] = {"section_type": RULES, "title": "이용 규칙", "body": "본문"}
    data.update(over)
    res = client.post(OP, data=json.dumps(data), content_type=JSON, headers=_auth(op))
    assert res.status_code == 201, res.content
    return res.json()


def _publish(client: Client, op: Account, sid: str) -> None:
    """Publish a section via the operator API."""
    res = client.post(f"{OP}/{sid}/publish", content_type=JSON, headers=_auth(op))
    assert res.status_code == 200, res.content


def test_operator_creates_lists_and_reads(client: Client) -> None:
    """An operator creates a draft, lists it, and reads its detail."""
    op = _account(Role.OPERATOR.value)
    body = _create(client, op)
    assert body["status"] == "draft"
    listed = client.get(OP, headers=_auth(op))
    assert listed.status_code == 200
    assert any(s["id"] == body["id"] for s in listed.json())
    detail = client.get(f"{OP}/{body['id']}", headers=_auth(op))
    assert detail.status_code == 200
    assert detail.json()["section_type"] == RULES


def test_duplicate_section_type_is_400(client: Client) -> None:
    """A second section of the same type is rejected."""
    op = _account(Role.OPERATOR.value)
    _create(client, op)
    dup = client.post(
        OP,
        data=json.dumps({"section_type": RULES, "title": "중복"}),
        content_type=JSON,
        headers=_auth(op),
    )
    assert dup.status_code == 400


def test_publish_makes_section_public_and_unpublish_hides_it(client: Client) -> None:
    """A draft is hidden publicly; publishing reveals it; unpublishing hides it."""
    op = _account(Role.OPERATOR.value)
    sid = _create(client, op)["id"]
    assert not any(s["id"] == sid for s in client.get(PUB).json())
    _publish(client, op, sid)
    pub = client.get(PUB)
    assert pub.status_code == 200
    assert any(s["id"] == sid for s in pub.json())
    unp = client.post(f"{OP}/{sid}/unpublish", content_type=JSON, headers=_auth(op))
    assert unp.status_code == 200
    assert not any(s["id"] == sid for s in client.get(PUB).json())


def test_public_read_needs_no_auth_and_draft_is_404(client: Client) -> None:
    """Published detail is readable without auth; a draft id is a 404 (no leak)."""
    op = _account(Role.OPERATOR.value)
    sid = _create(client, op)["id"]
    draft = client.get(f"{PUB}/{sid}")  # no auth header
    assert draft.status_code == 404  # draft hidden — no existence leak
    _publish(client, op, sid)
    pub = client.get(f"{PUB}/{sid}")  # no auth header
    assert pub.status_code == 200
    assert pub.json()["section_type"] == RULES
    # The public body carries no operator-only fields.
    assert "created_by_id" not in pub.json()


def test_published_section_cannot_be_edited(client: Client) -> None:
    """Editing a published section is refused (400); unpublish first."""
    op = _account(Role.OPERATOR.value)
    sid = _create(client, op)["id"]
    _publish(client, op, sid)
    res = client.post(
        f"{OP}/{sid}/update",
        data=json.dumps({"title": "몰래 수정"}),
        content_type=JSON,
        headers=_auth(op),
    )
    assert res.status_code == 400


def _ack(client: Client, account: Account, version: int) -> Any:
    """POST the rule acknowledgement with the version the fan read."""
    return client.post(
        f"{FAN}/acknowledge-rules",
        data=json.dumps({"version": version}),
        content_type=JSON,
        headers=_auth(account),
    )


def test_fan_acknowledges_published_rules(client: Client) -> None:
    """A fan acknowledges the published usage rules and gets the version back."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    sid = _create(client, op)["id"]
    _publish(client, op, sid)
    res = _ack(client, fan, 1)
    assert res.status_code == 200
    body = res.json()
    assert body["acknowledged"] is True
    assert body["version"] == 1


def test_stale_version_ack_is_409(client: Client) -> None:
    """An ack for a version that is no longer published is refused (409)."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    sid = _create(client, op)["id"]
    _publish(client, op, sid)  # v1
    # Republish to v2 (unpublish -> edit -> publish).
    client.post(f"{OP}/{sid}/unpublish", content_type=JSON, headers=_auth(op))
    client.post(
        f"{OP}/{sid}/update",
        data=json.dumps({"body": "개정"}),
        content_type=JSON,
        headers=_auth(op),
    )
    _publish(client, op, sid)  # v2
    stale = _ack(client, fan, 1)
    assert stale.status_code == 409
    assert _ack(client, fan, 2).status_code == 200


def test_acknowledge_without_published_rules_is_400(client: Client) -> None:
    """Acknowledging when no rules are published is refused (400)."""
    fan = _account(Role.FAN.value)
    assert _ack(client, fan, 1).status_code == 400


def test_staff_token_cannot_acknowledge(client: Client) -> None:
    """fan_auth is role-agnostic, so a staff token is refused on the fan POST (403)."""
    op = _account(Role.OPERATOR.value)
    sid = _create(client, op)["id"]
    _publish(client, op, sid)
    assert _ack(client, op, 1).status_code == 403


def test_operator_surface_refuses_fan_and_anonymous(client: Client) -> None:
    """The operator surface rejects fan tokens and anonymous callers."""
    fan = _account(Role.FAN.value)
    assert client.get(OP, headers=_auth(fan)).status_code in {401, 403}
    assert client.get(OP).status_code in {401, 403}
    assert client.post(f"{FAN}/acknowledge-rules", content_type=JSON).status_code in {401, 403}
