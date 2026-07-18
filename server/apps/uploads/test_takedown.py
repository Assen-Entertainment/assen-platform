"""Report-driven takedown: fan reports an image, operator actions it, it stops serving.

This is the whole justification for accepting user uploads without an automated
nudity/CSAM scanner (대표 approved 07-18): the moderation posture is *report-driven
human moderation*, so it is only real if the loop actually closes —

    upload → reportable → operator ACTIONED → the URL stops resolving

Each link is asserted here, plus the two invariants that make it safe: the row is
never deleted (append-only audit trail survives a takedown), and an image nobody
actioned keeps serving (no collateral 404s).

The reports themselves land in the existing operator queue (``GET /api/safety/
reports``) — there is no separate media queue — so that is asserted too.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import Client
from PIL import Image

from apps.audit.models import AuditAction, AuditEntry
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.safety.models import ReportStatus, SafetyReport
from apps.uploads.models import Upload, UploadStatus

pytestmark = pytest.mark.django_db

_PNG_BUF = BytesIO()
Image.new("RGB", (4, 4), color=(255, 0, 0)).save(_PNG_BUF, format="PNG")
PNG = _PNG_BUF.getvalue()


def _account(role: str) -> Account:
    return Account.objects.create(role=role)


def _auth(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _stored_upload(owner: Account) -> Upload:
    """Write a real object + row, mirroring what the upload endpoint produces."""
    name = default_storage.save("uploads/takedown-fixture.png", ContentFile(PNG))
    return Upload.objects.create(
        owner=owner, url=default_storage.url(name), content_type="image/png"
    )


def _fan_report(client: Client, fan: Account, upload: Upload) -> Any:
    return client.post(
        "/api/safety/fan-reports",
        data={"report_type": "photo_violation", "upload_id": str(upload.id)},
        content_type="application/json",
        headers=_auth(fan),
    )


def _action(client: Client, operator: Account, report_id: str) -> Any:
    return client.patch(
        f"/api/safety/reports/{report_id}/status",
        data={"status": ReportStatus.ACTIONED.value},
        content_type="application/json",
        headers=_auth(operator),
    )


# --- the loop -----------------------------------------------------------------


def test_fan_can_report_an_upload(client: Client) -> None:
    fan = _account(Role.FAN.value)
    upload = _stored_upload(_account(Role.FAN.value))

    res = _fan_report(client, fan, upload)

    assert res.status_code == 201, res.content
    report = SafetyReport.objects.get(id=res.json()["safety_report_id"])
    assert report.upload_id == upload.id
    assert report.reporter_id == fan.id


def test_actioning_the_report_takes_the_upload_down(client: Client) -> None:
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    upload = _stored_upload(_account(Role.FAN.value))
    report_id = _fan_report(client, fan, upload).json()["safety_report_id"]

    # Serving normally right up until the operator acts. The response is deliberately
    # left unclosed: the view opens nothing until the body is pulled, so an unread
    # response holds no handle and cannot block the takedown's move (on Windows an open
    # handle would). See test_media_url.test_serving_does_not_hold_the_object_open.
    assert client.get(upload.url).status_code == 200

    assert _action(client, operator, report_id).status_code == 200

    upload.refresh_from_db()
    assert upload.status == UploadStatus.TAKEN_DOWN.value
    # The headline assertion: the media URL stops resolving.
    assert client.get(upload.url).status_code == 404


def test_takedown_keeps_the_row_and_the_bytes(client: Client) -> None:
    # Append-only invariant (safety app): a takedown is a status change plus a MOVE,
    # never a delete — the row, its owner, the bytes, and the report that justified it
    # must all survive so the decision stays reviewable and reversible by a human.
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    upload = _stored_upload(_account(Role.FAN.value))
    report_id = _fan_report(client, fan, upload).json()["safety_report_id"]

    _action(client, operator, report_id)

    assert Upload.objects.filter(id=upload.id).exists()
    upload.refresh_from_db()
    # The bytes live on — at the quarantine key the takedown moved them to, not at the
    # served key (which must stop resolving; see apps/uploads/test_quarantine.py).
    assert default_storage.exists(upload.quarantine_key)
    assert not default_storage.exists(upload.url.split("/media/", 1)[1])
    assert SafetyReport.objects.get(id=report_id).upload_id == upload.id


def test_takedown_is_audited_against_the_report(client: Client) -> None:
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    upload = _stored_upload(_account(Role.FAN.value))
    report_id = _fan_report(client, fan, upload).json()["safety_report_id"]

    _action(client, operator, report_id)

    entry = AuditEntry.objects.get(action=AuditAction.UPLOAD_TAKEN_DOWN.value)
    assert entry.actor_id == operator.id
    assert entry.target == str(upload.id)
    # Ids only — the "why" stays in the report's restricted store, never the audit row.
    assert entry.metadata == {"safety_report_id": report_id}


def test_unactioned_upload_keeps_serving(client: Client) -> None:
    # A report alone must not remove content — only an operator's decision does.
    # Otherwise reporting would be a censorship button for any logged-in fan.
    fan = _account(Role.FAN.value)
    upload = _stored_upload(_account(Role.FAN.value))
    _fan_report(client, fan, upload)

    upload.refresh_from_db()
    assert upload.status == UploadStatus.VISIBLE.value
    assert client.get(upload.url).status_code == 200


def test_media_predating_the_upload_table_still_serves(client: Client) -> None:
    # Seeded/fixture media has no Upload row. The takedown check must not treat
    # "no row" as "taken down" and blanket-404 it.
    name = default_storage.save("uploads/seeded.png", ContentFile(PNG))
    assert client.get(default_storage.url(name)).status_code == 200


def test_second_report_actioned_on_an_already_down_upload_is_a_noop(client: Client) -> None:
    # One image can attract several reports; the second operator to act must not hit
    # an error for doing the right thing.
    operator = _account(Role.OPERATOR.value)
    upload = _stored_upload(_account(Role.FAN.value))
    first = _fan_report(client, _account(Role.FAN.value), upload).json()["safety_report_id"]
    second = _fan_report(client, _account(Role.FAN.value), upload).json()["safety_report_id"]

    assert _action(client, operator, first).status_code == 200
    assert _action(client, operator, second).status_code == 200

    upload.refresh_from_db()
    assert upload.status == UploadStatus.TAKEN_DOWN.value
    # Idempotent: the no-op second action adds no duplicate takedown audit row.
    assert AuditEntry.objects.filter(action=AuditAction.UPLOAD_TAKEN_DOWN.value).count() == 1


# --- the queue ----------------------------------------------------------------


def test_upload_reports_appear_in_the_operator_queue(client: Client) -> None:
    # There is no separate media-moderation queue by design: upload reports must show
    # up in the same triage list as every other report, or operators never see them.
    fan = _account(Role.FAN.value)
    operator = _account(Role.OPERATOR.value)
    upload = _stored_upload(_account(Role.FAN.value))
    report_id = _fan_report(client, fan, upload).json()["safety_report_id"]

    queue = client.get("/api/safety/reports", headers=_auth(operator))

    assert queue.status_code == 200
    assert report_id in {row["safety_report_id"] for row in queue.json()}


def test_unknown_upload_id_is_refused(client: Client) -> None:
    # A report filed against an id that resolves to nothing would never produce the
    # takedown the reporter expects, so it is refused rather than silently unbound.
    import uuid

    res = client.post(
        "/api/safety/fan-reports",
        data={"report_type": "photo_violation", "upload_id": str(uuid.uuid4())},
        content_type="application/json",
        headers=_auth(_account(Role.FAN.value)),
    )
    assert res.status_code == 422
    assert SafetyReport.objects.count() == 0
