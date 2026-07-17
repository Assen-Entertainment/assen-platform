"""Takedown reaches the object in STORAGE — the half a status flip cannot do.

``Upload.status`` moderates the reads that pass through Django's media route, which is
now all of them (apps.uploads.media serves every backend). That is the first line. But
it can only refuse a key it resolves back to a row, so anything reaching the bytes by
another route — a signed URL from an operator tool, a bucket-direct read, a row minted
under the legacy absolute-signed scheme — is answered only by the object no longer
being where it was.

So a takedown also moves the stored object to a quarantine key. That 404s the served
key in the store itself, which invalidates any outstanding signed URL (a signature
grants access to a key; there is nothing at that key any more), while the bytes survive
so an operator's mis-click stays reversible — the safety domain's append-only
invariant.

These tests assert the move on BOTH backends, because the bug was precisely that one
of them was never exercised:

- the local FileSystemStorage (dev/test), and
- an object store, via :class:`FakeObjectStorage` — which reproduces the S3 behaviour
  the local backend does not have: an absolute, *signed*, expiring ``url()``.

That signed ``url()`` is also why ``_stored_upload`` below still mints rows with it:
the upload endpoint no longer does (``Upload.url`` is now a stable, site-relative
function of the key — see test_media_url.py), so on the object-storage backend these
fixtures are exactly the **legacy row shape**, and asserting the move against them is
what keeps takedown working for rows written before the scheme was stabilised.

Plus the ordering that makes the move safe against a non-transactional storage: every
failure must leave the content **not served**.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pytest
from django.core.files.base import ContentFile, File
from django.core.files.storage import Storage, default_storage
from django.test import Client, override_settings
from PIL import Image

from apps.audit.models import AuditAction, AuditEntry
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.safety.models import ReportStatus, SafetyReport
from apps.safety.services import change_report_status, file_fan_report, resolve_report
from apps.uploads.models import Upload, UploadStatus
from apps.uploads.services import (
    quarantine_key_for,
    restore_upload,
    served_object_key,
    take_down_upload,
)

pytestmark = pytest.mark.django_db

_PNG_BUF = BytesIO()
Image.new("RGB", (4, 4), color=(255, 0, 0)).save(_PNG_BUF, format="PNG")
PNG = _PNG_BUF.getvalue()


# --- an object-storage stand-in ------------------------------------------------

_BUCKET = "assen-media-test"
_BUCKET_OBJECTS: dict[str, bytes] = {}


class FakeObjectStorage(Storage):
    """In-memory storage shaped like the S3 backend where it matters here.

    Not a general-purpose fake. It reproduces exactly the two production behaviours
    FileSystemStorage does *not* have, and which are the reason the status-only
    takedown was ineffective:

    - ``url()`` returns an absolute, signed, expiring bucket URL rather than
      ``MEDIA_URL`` + key. That is what ``Upload.url`` really holds in production, and
      what ``served_object_key`` must invert to find the object at all.
    - the bytes are reachable only at their key. Nothing consults Django, so no
      ``status`` check can intervene — the object resolves or it does not.

    moto is not a dependency of this project and is not added for this: these tests
    need a storage backend's *contract*, not a bucket, and everything below drives the
    same ``default_storage`` API production calls.
    """

    def __init__(self, **options: Any) -> None:
        """Accept (and ignore) the settings OPTIONS block, as a real backend does."""
        self.options = options

    def _open(self, name: str, mode: str = "rb") -> File[Any]:
        return ContentFile(_BUCKET_OBJECTS[name], name=name)

    def _save(self, name: str, content: File[Any]) -> str:
        _BUCKET_OBJECTS[name] = b"".join(content.chunks())
        return name

    def exists(self, name: str) -> bool:
        return name in _BUCKET_OBJECTS

    def delete(self, name: str) -> None:
        _BUCKET_OBJECTS.pop(name, None)

    def size(self, name: str) -> int:
        return len(_BUCKET_OBJECTS[name])

    def url(self, name: str | None) -> str:
        """A signed, expiring, virtual-hosted-style bucket URL (querystring_auth)."""
        return (
            f"https://{_BUCKET}.s3.ap-northeast-2.amazonaws.com/{name}"
            "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Expires=3600"
            "&X-Amz-Signature=0000000000000000000000000000000000000000000000000000000000000000"
        )


class UnreadableObjectStorage(FakeObjectStorage):
    """An object store whose reads fail — the storage half of a takedown breaking."""

    def _open(self, name: str, mode: str = "rb") -> File[Any]:
        raise OSError("bucket unreachable")


def _storages(backend: str) -> dict[str, dict[str, Any]]:
    return {
        "default": {"BACKEND": backend, "OPTIONS": {"bucket_name": _BUCKET}},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


_OBJECT_STORAGE = _storages(f"{__name__}.FakeObjectStorage")
_BROKEN_STORAGE = _storages(f"{__name__}.UnreadableObjectStorage")


@pytest.fixture(autouse=True)
def _empty_bucket() -> None:
    """The fake bucket is module state; no test may see another's objects."""
    _BUCKET_OBJECTS.clear()


# --- fixtures ------------------------------------------------------------------


def _account(role: str) -> Account:
    return Account.objects.create(role=role)


def _auth(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _stored_upload(*, name: str = "uploads/quarantine-fixture.png") -> Upload:
    """Write a real object + row through the storage API, as the endpoint does."""
    stored = default_storage.save(name, ContentFile(PNG))
    return Upload.objects.create(
        owner=_account(Role.FAN.value),
        url=default_storage.url(stored),
        content_type="image/png",
    )


# --- the move, on the local filesystem -----------------------------------------


def test_takedown_moves_the_object_out_of_the_served_key() -> None:
    # The headline: the served key must stop resolving in STORAGE, not just in the
    # view — that is what invalidates an already-issued signed URL.
    operator = _account(Role.OPERATOR.value)
    upload = _stored_upload()
    served_key = served_object_key(upload.url)
    assert default_storage.exists(served_key)

    take_down_upload(upload=upload, actor=operator)

    assert not default_storage.exists(served_key)
    assert default_storage.exists(quarantine_key_for(served_key))


def test_takedown_keeps_the_bytes_and_records_where_they_went() -> None:
    # Append-only / human-reversible: the bytes survive, and the row says where, so a
    # restore is deterministic rather than a search.
    operator = _account(Role.OPERATOR.value)
    upload = _stored_upload()
    served_key = served_object_key(upload.url)

    take_down_upload(upload=upload, actor=operator)

    upload.refresh_from_db()
    assert upload.status == UploadStatus.TAKEN_DOWN.value
    assert upload.quarantine_key == quarantine_key_for(served_key)
    with default_storage.open(upload.quarantine_key, "rb") as handle:
        assert handle.read() == PNG
    # ``url`` is never mutated — it stays the record of the key to restore back to.
    assert served_object_key(upload.url) == served_key


def test_the_quarantined_object_is_not_servable_from_its_new_key(client: Client) -> None:
    # The quarantine prefix lives inside MEDIA_ROOT on this backend, and its key is
    # trivially derivable from the original. Serving it would hand back exactly the
    # image the operator removed.
    operator = _account(Role.OPERATOR.value)
    upload = _stored_upload()
    take_down_upload(upload=upload, actor=operator)
    upload.refresh_from_db()

    assert client.get(f"/media/{upload.quarantine_key}").status_code == 404
    # ...and the original URL is gone too (the row's check and the moved object agree).
    assert client.get(upload.url).status_code == 404


def test_restore_moves_the_object_back_and_serves_again(
    client: Client, django_capture_on_commit_callbacks: Any
) -> None:
    operator = _account(Role.OPERATOR.value)
    upload = _stored_upload()
    served_key = served_object_key(upload.url)
    take_down_upload(upload=upload, actor=operator)

    with django_capture_on_commit_callbacks(execute=True):
        restore_upload(upload=upload, actor=operator)

    upload.refresh_from_db()
    assert upload.status == UploadStatus.VISIBLE.value
    assert upload.quarantine_key == ""
    assert default_storage.exists(served_key)
    assert not default_storage.exists(quarantine_key_for(served_key))
    assert client.get(upload.url).status_code == 200


def test_restore_is_audited_against_the_report(
    django_capture_on_commit_callbacks: Any,
) -> None:
    # A mis-click that removed a creator's image and its reversal are both accountable.
    operator = _account(Role.OPERATOR.value)
    upload = _stored_upload()
    take_down_upload(upload=upload, actor=operator)

    with django_capture_on_commit_callbacks(execute=True):
        restore_upload(upload=upload, actor=operator, report_id="r-1")

    entry = AuditEntry.objects.get(action=AuditAction.UPLOAD_RESTORED.value)
    assert entry.actor_id == operator.id
    assert entry.target == str(upload.id)
    assert entry.metadata == {"safety_report_id": "r-1"}


# --- idempotency ---------------------------------------------------------------


def test_double_takedown_neither_loses_the_object_nor_crashes() -> None:
    operator = _account(Role.OPERATOR.value)
    upload = _stored_upload()
    served_key = served_object_key(upload.url)

    take_down_upload(upload=upload, actor=operator)
    take_down_upload(upload=upload, actor=operator)

    upload.refresh_from_db()
    assert upload.status == UploadStatus.TAKEN_DOWN.value
    assert default_storage.exists(quarantine_key_for(served_key))
    assert not default_storage.exists(served_key)
    assert AuditEntry.objects.filter(action=AuditAction.UPLOAD_TAKEN_DOWN.value).count() == 1


def test_double_restore_neither_loses_the_object_nor_crashes(
    django_capture_on_commit_callbacks: Any,
) -> None:
    operator = _account(Role.OPERATOR.value)
    upload = _stored_upload()
    served_key = served_object_key(upload.url)
    take_down_upload(upload=upload, actor=operator)

    with django_capture_on_commit_callbacks(execute=True):
        restore_upload(upload=upload, actor=operator)
    with django_capture_on_commit_callbacks(execute=True):
        restore_upload(upload=upload, actor=operator)

    upload.refresh_from_db()
    assert upload.status == UploadStatus.VISIBLE.value
    assert default_storage.exists(served_key)
    with default_storage.open(served_key, "rb") as handle:
        assert handle.read() == PNG
    assert AuditEntry.objects.filter(action=AuditAction.UPLOAD_RESTORED.value).count() == 1


def test_takedown_self_heals_a_move_whose_db_write_was_lost() -> None:
    # The tolerated mismatch: the move committed to storage but the transaction rolled
    # back, so the row still says visible while the bytes are already out of the served
    # key. Re-running the operator's action must CONVERGE, not short-circuit on the
    # stale row and leave the takedown half-recorded forever.
    operator = _account(Role.OPERATOR.value)
    upload = _stored_upload()
    served_key = served_object_key(upload.url)
    take_down_upload(upload=upload, actor=operator)
    # Rewind the DB half only, exactly as a rollback would have left it.
    Upload.objects.filter(id=upload.id).update(
        status=UploadStatus.VISIBLE.value, quarantine_key=""
    )
    upload.refresh_from_db()

    take_down_upload(upload=upload, actor=operator)

    upload.refresh_from_db()
    assert upload.status == UploadStatus.TAKEN_DOWN.value
    assert upload.quarantine_key == quarantine_key_for(served_key)
    assert default_storage.exists(upload.quarantine_key)


def test_restore_self_heals_a_move_back_that_never_ran(
    django_capture_on_commit_callbacks: Any,
) -> None:
    # The mirror case: the restore's DB write committed but the deferred move-back
    # failed, leaving a visible row whose object is still quarantined (image down —
    # the safe direction). Re-running the un-action must finish the move.
    operator = _account(Role.OPERATOR.value)
    upload = _stored_upload()
    served_key = served_object_key(upload.url)
    take_down_upload(upload=upload, actor=operator)
    with django_capture_on_commit_callbacks(execute=False):
        restore_upload(upload=upload, actor=operator)  # callback captured, never run
    upload.refresh_from_db()
    assert upload.status == UploadStatus.VISIBLE.value
    assert not default_storage.exists(served_key)

    with django_capture_on_commit_callbacks(execute=True):
        restore_upload(upload=upload, actor=operator)

    assert default_storage.exists(served_key)


# --- failure semantics: every failure leaves the content NOT served -------------


@override_settings(STORAGES=_BROKEN_STORAGE)
def test_takedown_whose_move_fails_raises_and_leaves_the_row_visible() -> None:
    # The forbidden state is "DB claims the image is down while the bytes are still
    # served". So a move that cannot happen must fail loudly, before the DB write —
    # never record a takedown that did not take effect.
    operator = _account(Role.OPERATOR.value)
    upload = _stored_upload()
    served_key = served_object_key(upload.url)

    with pytest.raises(OSError):
        take_down_upload(upload=upload, actor=operator)

    upload.refresh_from_db()
    assert upload.status == UploadStatus.VISIBLE.value
    assert upload.quarantine_key == ""
    # Still served — honest: nothing claims otherwise, and the operator can retry.
    assert default_storage.exists(served_key)
    assert AuditEntry.objects.filter(action=AuditAction.UPLOAD_TAKEN_DOWN.value).count() == 0


@override_settings(STORAGES=_BROKEN_STORAGE)
def test_a_failed_move_rolls_the_report_back_to_unactioned() -> None:
    # The same invariant one level up: an ACTIONED report and a still-served image must
    # never be observable together, so the storage failure must take the report's status
    # change down with it (the takedown runs inside change_report_status's transaction).
    operator = _account(Role.OPERATOR.value)
    upload = _stored_upload()
    report = file_fan_report(
        reporter=_account(Role.FAN.value), report_type="photo_violation", upload=upload
    )

    with pytest.raises(OSError):
        change_report_status(report=report, status=ReportStatus.ACTIONED.value, actor=operator)

    report.refresh_from_db()
    assert report.status == ReportStatus.RECEIVED.value
    assert Upload.objects.get(id=upload.id).status == UploadStatus.VISIBLE.value


# --- the object-storage (S3-ish) path ------------------------------------------


@override_settings(STORAGES=_OBJECT_STORAGE)
def test_served_key_is_derived_from_a_signed_bucket_url() -> None:
    # The production shape of Upload.url: absolute, signed, expiring. If the key cannot
    # be recovered from it, a takedown on S3 cannot find the object to move at all.
    upload = _stored_upload(name="uploads/abc123.png")

    assert upload.url.startswith(f"https://{_BUCKET}.s3.ap-northeast-2.amazonaws.com/")
    assert "X-Amz-Signature=" in upload.url
    assert served_object_key(upload.url) == "uploads/abc123.png"


@override_settings(STORAGES=_OBJECT_STORAGE)
def test_takedown_moves_the_object_in_the_bucket() -> None:
    # The gap this closes: on this backend nothing consults Django, so the status flip
    # alone changed nothing. The object itself has to leave the served key.
    operator = _account(Role.OPERATOR.value)
    upload = _stored_upload()
    served_key = served_object_key(upload.url)
    issued_signed_url = upload.url  # a signature handed out before the takedown

    take_down_upload(upload=upload, actor=operator)

    # Every outstanding signed URL points at this key; it now resolves to nothing.
    assert served_object_key(issued_signed_url) == served_key
    assert not default_storage.exists(served_key)
    assert default_storage.exists(quarantine_key_for(served_key))
    assert _BUCKET_OBJECTS[quarantine_key_for(served_key)] == PNG


@override_settings(STORAGES=_OBJECT_STORAGE)
def test_restore_moves_the_object_back_in_the_bucket(
    django_capture_on_commit_callbacks: Any,
) -> None:
    operator = _account(Role.OPERATOR.value)
    upload = _stored_upload()
    served_key = served_object_key(upload.url)
    take_down_upload(upload=upload, actor=operator)

    with django_capture_on_commit_callbacks(execute=True):
        restore_upload(upload=upload, actor=operator)

    upload.refresh_from_db()
    assert upload.status == UploadStatus.VISIBLE.value
    assert _BUCKET_OBJECTS[served_key] == PNG
    assert quarantine_key_for(served_key) not in _BUCKET_OBJECTS


# --- wiring: the operator's un-action ------------------------------------------


def _actioned(client: Client, operator: Account, upload: Upload) -> SafetyReport:
    report = file_fan_report(
        reporter=_account(Role.FAN.value), report_type="photo_violation", upload=upload
    )
    res = client.patch(
        f"/api/safety/reports/{report.id}/status",
        data={"status": ReportStatus.ACTIONED.value},
        content_type="application/json",
        headers=_auth(operator),
    )
    assert res.status_code == 200, res.content
    return report


def test_unactioning_the_report_restores_the_image(
    client: Client, django_capture_on_commit_callbacks: Any
) -> None:
    # The safety app has no dedicated un-action endpoint, but PATCH .../status accepts
    # the reverse transition (it validates only that CLOSED goes through resolve_report)
    # — so moving an actioned report back to reviewing IS the un-action, and it must
    # undo the takedown.
    operator = _account(Role.OPERATOR.value)
    upload = _stored_upload()
    served_key = served_object_key(upload.url)
    report = _actioned(client, operator, upload)
    assert not default_storage.exists(served_key)

    with django_capture_on_commit_callbacks(execute=True):
        res = client.patch(
            f"/api/safety/reports/{report.id}/status",
            data={"status": ReportStatus.REVIEWING.value},
            content_type="application/json",
            headers=_auth(operator),
        )

    assert res.status_code == 200, res.content
    upload.refresh_from_db()
    assert upload.status == UploadStatus.VISIBLE.value
    assert default_storage.exists(served_key)
    assert client.get(upload.url).status_code == 200


def test_unactioning_one_of_two_actioned_reports_keeps_the_image_down(
    client: Client, django_capture_on_commit_callbacks: Any
) -> None:
    # One image can attract several reports. Reverting one operator's call must not
    # silently undo another's — only the last one holding the image down may restore it.
    operator = _account(Role.OPERATOR.value)
    upload = _stored_upload()
    served_key = served_object_key(upload.url)
    first = _actioned(client, operator, upload)
    _actioned(client, operator, upload)

    with django_capture_on_commit_callbacks(execute=True):
        res = client.patch(
            f"/api/safety/reports/{first.id}/status",
            data={"status": ReportStatus.REVIEWING.value},
            content_type="application/json",
            headers=_auth(operator),
        )

    assert res.status_code == 200, res.content
    upload.refresh_from_db()
    assert upload.status == UploadStatus.TAKEN_DOWN.value
    assert not default_storage.exists(served_key)


def test_closing_an_actioned_report_keeps_the_image_down(
    client: Client, django_capture_on_commit_callbacks: Any
) -> None:
    # Closing is not an un-action: actioned→closed is the normal end state of a report
    # whose content was removed, and resolving it must not put the image back.
    operator = _account(Role.OPERATOR.value)
    upload = _stored_upload()
    served_key = served_object_key(upload.url)
    report = _actioned(client, operator, upload)

    with django_capture_on_commit_callbacks(execute=True):
        resolve_report(
            report=report, resolution="removed", resolution_note="", actor=operator
        )

    upload.refresh_from_db()
    assert upload.status == UploadStatus.TAKEN_DOWN.value
    assert not default_storage.exists(served_key)
