"""Tests for the event-campaign API (F10, ASS-107 v0).

Covers the operator surface (create/list/detail/update/publish/unpublish/close,
per-campaign reservations), the fan surface (published-only list, impression,
reserve/waitlist, list/cancel own), and the gates: operator role, fan role,
ownership, blocked fan, publication visibility, and anonymous.
"""

from __future__ import annotations

import json
import uuid
from datetime import timedelta
from typing import Any

import pytest
from django.test import Client
from django.utils import timezone

from apps.event_campaign.models import EventReservation
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.safety.models import BlockScope, UserBlock

pytestmark = pytest.mark.django_db

OP = "/api/operator/event-campaigns"
FANC = "/api/fan/event-campaigns"
FANR = "/api/fan/event-reservations"
JSON = "application/json"


def _account(role: str) -> Account:
    """Create an account with the requested role."""
    return Account.objects.create(role=role)


def _auth(account: Account) -> dict[str, str]:
    """Return a Django test-client ``headers`` mapping for an issued token."""
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _future(days: int) -> str:
    """ISO datetime string ``days`` in the future."""
    return (timezone.now() + timedelta(days=days)).isoformat()


def _create(client: Client, op: Account, **over: object) -> Any:
    """Create a draft campaign via the operator API and return the body."""
    data: dict[str, object] = {
        "title": "Birthday Live",
        "starts_at": _future(7),
        "event_type": "birthday",
    }
    data.update(over)
    res = client.post(OP, data=json.dumps(data), content_type=JSON, headers=_auth(op))
    assert res.status_code == 201, res.content
    return res.json()


def _publish(client: Client, op: Account, cid: str) -> None:
    """Publish a campaign via the operator API."""
    res = client.post(f"{OP}/{cid}/publish", content_type=JSON, headers=_auth(op))
    assert res.status_code == 200, res.content


def test_operator_creates_lists_and_reads(client: Client) -> None:
    """An operator creates a draft, lists it, and reads its detail."""
    op = _account(Role.OPERATOR.value)
    body = _create(client, op)
    assert body["status"] == "draft"

    listed = client.get(OP, headers=_auth(op))
    assert listed.status_code == 200
    assert any(c["id"] == body["id"] for c in listed.json())

    detail = client.get(f"{OP}/{body['id']}", headers=_auth(op))
    assert detail.status_code == 200
    assert detail.json()["title"] == "Birthday Live"


def test_operator_create_unknown_cast_is_404(client: Client) -> None:
    """Referencing a non-existent cast id is a 404."""
    op = _account(Role.OPERATOR.value)
    res = client.post(
        OP,
        data=json.dumps({"title": "x", "starts_at": _future(3), "cast_id": str(uuid.uuid4())}),
        content_type=JSON,
        headers=_auth(op),
    )
    assert res.status_code == 404


def test_publish_makes_campaign_fan_visible(client: Client) -> None:
    """A draft is hidden from fans; publishing reveals it; unpublishing hides it."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    body = _create(client, op)
    cid = body["id"]

    # Draft: not in the fan list.
    assert not any(c["id"] == cid for c in client.get(FANC, headers=_auth(fan)).json())
    _publish(client, op, cid)
    assert any(c["id"] == cid for c in client.get(FANC, headers=_auth(fan)).json())

    unp = client.post(f"{OP}/{cid}/unpublish", content_type=JSON, headers=_auth(op))
    assert unp.status_code == 200
    assert not any(c["id"] == cid for c in client.get(FANC, headers=_auth(fan)).json())


def test_operator_update_and_close(client: Client) -> None:
    """An operator edits then closes a campaign."""
    op = _account(Role.OPERATOR.value)
    cid = _create(client, op)["id"]
    upd = client.post(
        f"{OP}/{cid}/update",
        data=json.dumps({"title": "Renamed"}),
        content_type=JSON,
        headers=_auth(op),
    )
    assert upd.status_code == 200
    assert upd.json()["title"] == "Renamed"
    closed = client.post(f"{OP}/{cid}/close", content_type=JSON, headers=_auth(op))
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"


def test_fan_views_published_but_not_draft(client: Client) -> None:
    """A fan impression works on a published campaign and 400s on a draft."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    cid = _create(client, op)["id"]
    draft_view = client.post(f"{FANC}/{cid}/view", content_type=JSON, headers=_auth(fan))
    assert draft_view.status_code == 404  # draft hidden — no existence leak
    _publish(client, op, cid)
    pub_view = client.post(f"{FANC}/{cid}/view", content_type=JSON, headers=_auth(fan))
    assert pub_view.status_code == 200


def test_fan_reserves_and_lists_own(client: Client) -> None:
    """A fan reserves a published campaign and sees it in their reservations."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    cid = _create(client, op)["id"]
    _publish(client, op, cid)
    res = client.post(
        f"{FANC}/{cid}/reserve",
        data=json.dumps({"status": "reserved"}),
        content_type=JSON,
        headers=_auth(fan),
    )
    assert res.status_code == 201
    rid = res.json()["id"]
    mine = client.get(FANR, headers=_auth(fan))
    assert mine.status_code == 200
    assert any(r["id"] == rid for r in mine.json())


def test_fan_cannot_reserve_draft(client: Client) -> None:
    """Reserving a draft campaign is refused (400)."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    cid = _create(client, op)["id"]
    res = client.post(f"{FANC}/{cid}/reserve", content_type=JSON, headers=_auth(fan))
    assert res.status_code == 404  # draft hidden — no existence leak


def test_blocked_fan_cannot_reserve(client: Client) -> None:
    """A blocked fan cannot reserve an event (400)."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    UserBlock.objects.create(
        target=fan,
        block_scope=BlockScope.FANDOM_FEATURE.value,
        block_reason="policy_violation",
        effective_from=timezone.now(),
        created_by=_account(Role.MANAGER.value),
    )
    cid = _create(client, op)["id"]
    _publish(client, op, cid)
    res = client.post(f"{FANC}/{cid}/reserve", content_type=JSON, headers=_auth(fan))
    assert res.status_code == 400


def test_duplicate_reserve_is_400(client: Client) -> None:
    """A second active reservation on the same campaign is rejected."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    cid = _create(client, op)["id"]
    _publish(client, op, cid)
    first = client.post(f"{FANC}/{cid}/reserve", content_type=JSON, headers=_auth(fan))
    assert first.status_code == 201
    dup = client.post(f"{FANC}/{cid}/reserve", content_type=JSON, headers=_auth(fan))
    assert dup.status_code == 400


def test_staff_token_cannot_reserve(client: Client) -> None:
    """fan_auth is role-agnostic, so a staff token is refused on reserve (403)."""
    op = _account(Role.OPERATOR.value)
    cid = _create(client, op)["id"]
    _publish(client, op, cid)
    res = client.post(f"{FANC}/{cid}/reserve", content_type=JSON, headers=_auth(op))
    assert res.status_code == 403


def test_fan_cancels_own_not_others(client: Client) -> None:
    """A fan cancels their own reservation; another fan's id is a 404."""
    op = _account(Role.OPERATOR.value)
    owner = _account(Role.FAN.value)
    other = _account(Role.FAN.value)
    cid = _create(client, op)["id"]
    _publish(client, op, cid)
    rid = client.post(f"{FANC}/{cid}/reserve", content_type=JSON, headers=_auth(owner)).json()["id"]

    foreign = client.post(f"{FANR}/{rid}/cancel", content_type=JSON, headers=_auth(other))
    assert foreign.status_code == 404
    mine = client.post(f"{FANR}/{rid}/cancel", content_type=JSON, headers=_auth(owner))
    assert mine.status_code == 200
    assert mine.json()["status"] == "cancelled"


def test_operator_lists_campaign_reservations(client: Client) -> None:
    """An operator sees the reservations recorded against a campaign."""
    op = _account(Role.OPERATOR.value)
    fan = _account(Role.FAN.value)
    cid = _create(client, op)["id"]
    _publish(client, op, cid)
    client.post(f"{FANC}/{cid}/reserve", content_type=JSON, headers=_auth(fan))
    rows = client.get(f"{OP}/{cid}/reservations", headers=_auth(op))
    assert rows.status_code == 200
    assert len(rows.json()) == 1
    assert EventReservation.objects.filter(campaign_id=cid).count() == 1


def test_operator_surface_refuses_fan_and_anonymous(client: Client) -> None:
    """The operator surface rejects fan tokens and anonymous callers."""
    fan = _account(Role.FAN.value)
    assert client.get(OP, headers=_auth(fan)).status_code in {401, 403}
    assert client.get(OP).status_code in {401, 403}
    assert client.get(FANC).status_code in {401, 403}
