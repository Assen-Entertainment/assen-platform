"""The upload-availability gate matrix (ALLOW_UPLOADS x storage backend).

The upload surface has exactly one switch, ``ALLOW_UPLOADS``, plus one question it
cannot answer by itself: can the storage backend actually hold the object? That second
half is the invariant this file protects — never accept an upload that cannot come
back — and it is all that remains of a longer story. ``ALLOW_UPLOADS`` was once fused
with ``SERVE_LOCAL_MEDIA`` into a single flag, which made production uploads impossible
(prod needed accept ON with local serving OFF, a state one flag could not express);
splitting them fixed that, and ``SERVE_LOCAL_MEDIA`` was then retired entirely when
Django became the serving path for every backend, at which point "does a serving path
exist" stopped being a question anyone can answer no to.

So the matrix, all four cells:

    ALLOW_UPLOADS   storage backend         expected
    off             (any)                   503  — not enabled here
    on              S3 backend, no bucket   503  — nothing could hold it
    on              local filesystem        201  — dev/test/demo
    on              S3 backend + bucket     201  — production

The 503 cases must stay 503 for the *right* reason, so each asserts the coded error
and that no row was written.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pytest
from django.core.files.storage import default_storage
from django.test import Client, override_settings
from PIL import Image

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.uploads.api import uploads_enabled
from apps.uploads.models import Upload
from config.storage import media_storage_ready

pytestmark = pytest.mark.django_db

URL = "/api/uploads"

# A real, decodable PNG — the gate must be what refuses these, never the validator.
_PNG_BUF = BytesIO()
Image.new("RGB", (4, 4), color=(0, 128, 255)).save(_PNG_BUF, format="PNG")
PNG = _PNG_BUF.getvalue()

# An S3 STORAGES block shaped like the one config.settings.base builds when
# DJANGO_MEDIA_S3_BUCKET is set. Never actually written to: these tests only assert
# the *gate's* verdict, and the 201 case is covered separately with local storage
# (and end-to-end against an object-storage double in test_media_url.py).
_S3_STORAGES: dict[str, dict[str, Any]] = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {"bucket_name": "assen-media-test", "querystring_auth": True},
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# The same backend with no bucket named — the misconfiguration the storage half of the
# gate exists to catch, and the one most likely to reach production (an empty
# DJANGO_MEDIA_S3_BUCKET is silent, and the BACKEND alone still looks correct).
_S3_NO_BUCKET: dict[str, dict[str, Any]] = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {"bucket_name": ""},
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

_LOCAL_STORAGES: dict[str, dict[str, Any]] = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def _fan() -> Account:
    return Account.objects.create(role=Role.FAN.value)


def _auth(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _upload(client: Client, account: Account) -> Any:
    from django.core.files.uploadedfile import SimpleUploadedFile

    return client.post(
        URL,
        {"file": SimpleUploadedFile("x.png", PNG, content_type="image/png")},
        headers=_auth(account),
    )


# --- the four cells -----------------------------------------------------------


@override_settings(ALLOW_UPLOADS=False, STORAGES=_LOCAL_STORAGES)
def test_uploads_off_refuses_even_with_usable_storage(client: Client) -> None:
    # ALLOW_UPLOADS is the accept decision and it is not overridable by the storage
    # being perfectly fine — otherwise the flag would not be a gate at all.
    res = _upload(client, _fan())
    assert res.status_code == 503
    assert res.json()["code"] == "UploadStorageUnavailable"
    assert Upload.objects.count() == 0


@override_settings(ALLOW_UPLOADS=True, STORAGES=_S3_NO_BUCKET)
def test_uploads_on_without_usable_storage_refuses(client: Client) -> None:
    # The invariant carried over from the old single flag: enabling uploads is not
    # enough. An object-storage backend with no bucket can hold nothing, so an accepted
    # file would be written nowhere and every save() would blow up mid-request.
    res = _upload(client, _fan())
    assert res.status_code == 503
    assert res.json()["code"] == "UploadStorageUnavailable"
    assert Upload.objects.count() == 0


@override_settings(ALLOW_UPLOADS=True, STORAGES=_LOCAL_STORAGES)
def test_uploads_on_with_local_storage_accepts(client: Client) -> None:
    fan = _fan()
    res = _upload(client, fan)
    assert res.status_code == 201, res.content
    url = res.json()["url"]
    assert url.startswith("/media/uploads/")
    assert default_storage.exists(url.split("/media/", 1)[1])
    assert Upload.objects.filter(owner=fan).count() == 1


@override_settings(ALLOW_UPLOADS=True, STORAGES=_S3_STORAGES)
def test_uploads_on_with_s3_configured_accepts() -> None:
    # The production posture — accept ON, S3 wired — which the pre-split flag could not
    # express and which therefore 503'd every prod upload. Asserted at the gate rather
    # than through HTTP: a 201 here would demand a real bucket, and the only thing this
    # cell is about is that the gate says yes. The 201 itself is asserted against an
    # object-storage double in test_media_url.py.
    assert uploads_enabled() is True


# --- the storage-readiness predicate -------------------------------------------


@override_settings(STORAGES=_S3_STORAGES)
def test_media_storage_ready_true_for_s3_backend_with_a_bucket() -> None:
    assert media_storage_ready() is True


@override_settings(STORAGES=_LOCAL_STORAGES)
def test_media_storage_ready_true_for_local_filesystem() -> None:
    # The local filesystem is a usable store, and Django serves it back like any other
    # backend — so there is nothing here to refuse. (This answered False while the
    # predicate meant "is a real object store wired", back when it was also standing in
    # for "can anything serve reads".)
    assert media_storage_ready() is True


@override_settings(STORAGES=_S3_NO_BUCKET)
def test_media_storage_ready_false_for_s3_without_a_bucket() -> None:
    # A backend pointed at no bucket holds nothing, so it must not read as "ready" —
    # this is the misconfiguration most likely to reach production, because the backend
    # name alone looks correct.
    assert media_storage_ready() is False


@override_settings(ALLOW_UPLOADS=True, STORAGES=_S3_NO_BUCKET)
def test_uploads_enabled_false_when_storage_cannot_hold_it() -> None:
    assert uploads_enabled() is False


@override_settings(ALLOW_UPLOADS=False, STORAGES=_S3_STORAGES)
def test_uploads_enabled_false_when_not_allowed() -> None:
    assert uploads_enabled() is False
