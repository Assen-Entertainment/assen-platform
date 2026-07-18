"""The media URL is STABLE, and Django serves it on every backend.

The bug this file exists to prevent: ``Upload.url`` was minted with
``default_storage.url()``. On the local filesystem that returns ``MEDIA_URL`` + key and
everything looked fine — but production configures S3 with ``querystring_auth``, where
the same call returns a **signed URL that expires in about an hour**. That value is
persisted on the row and copied verbatim into Post/Product ``media_url``, so every
image in production would have broken roughly an hour after it was uploaded. The local
backend could never have shown it.

So the fix is asserted against an object-storage backend whose ``url()`` behaves like
the real one — :class:`~apps.uploads.test_quarantine.FakeObjectStorage`, reused rather
than re-declared so these tests and the takedown tests cannot drift apart about what S3
does. Every test below that matters runs on a backend where the old code produced a
signature.

Two properties, and they are the same decision seen from both ends (대표 approved
07-18: serve media through Django, on every backend):

- what is **written** is a pure function of the storage key — identical on the local
  filesystem and on S3, and without a lifetime;
- what is **served** comes back through the gated view on both backends, which is what
  keeps the URL honest (nothing expires) and a takedown immediate (every read is
  checked, and there is no edge copy to purge).
"""

from __future__ import annotations

from collections.abc import Iterator
from io import BytesIO
from typing import Any, cast

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import StreamingHttpResponse
from django.test import Client, override_settings
from PIL import Image

from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.uploads.models import Upload, UploadStatus
from apps.uploads.services import (
    quarantine_key_for,
    restore_upload,
    served_object_key,
    take_down_upload,
)
from apps.uploads.test_quarantine import _BUCKET_OBJECTS, FakeObjectStorage

pytestmark = pytest.mark.django_db

URL = "/api/uploads"

_OBJECT_STORAGE: dict[str, dict[str, Any]] = {
    "default": {
        "BACKEND": f"{FakeObjectStorage.__module__}.{FakeObjectStorage.__qualname__}",
        "OPTIONS": {"bucket_name": "assen-media-test"},
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def _image(fmt: str) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (4, 4), color=(255, 0, 0)).save(buf, format=fmt)
    return buf.getvalue()


PNG = _image("PNG")
WEBP = _image("WEBP")


@pytest.fixture(autouse=True)
def _empty_bucket() -> None:
    """The fake bucket is module state; no test may see another's objects."""
    _BUCKET_OBJECTS.clear()


def _fan() -> Account:
    return Account.objects.create(role=Role.FAN.value)


def _auth(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _upload(
    client: Client, data: bytes = PNG, *, name: str = "x.png", content_type: str = "image/png"
) -> Any:
    return client.post(
        URL,
        {"file": SimpleUploadedFile(name, data, content_type=content_type)},
        headers=_auth(_fan()),
    )


# --- what gets minted ----------------------------------------------------------


def test_local_backend_mints_a_stable_site_relative_url(client: Client) -> None:
    res = _upload(client)

    assert res.status_code == 201, res.content
    url = res.json()["url"]
    assert url.startswith("/media/uploads/")
    assert "?" not in url  # nothing to expire


@override_settings(STORAGES=_OBJECT_STORAGE)
def test_object_storage_mints_the_same_url_and_it_carries_no_signature(
    client: Client,
) -> None:
    # THE regression. On this backend the old write path stored what the next assertion
    # proves url() still returns: a signed, expiring, absolute bucket URL.
    res = _upload(client)

    assert res.status_code == 201, res.content
    url = res.json()["url"]
    assert url.startswith("/media/uploads/")
    assert not url.startswith("http")
    assert "?" not in url
    for signature_marker in ("X-Amz-Signature", "X-Amz-Expires", "X-Amz-Algorithm"):
        assert signature_marker not in url

    # The backend really would have handed us an expiring URL — i.e. this test is not
    # vacuously passing against a fake that behaves like the local filesystem.
    signed = default_storage.url(served_object_key(url))
    assert signed.startswith("https://")
    assert "X-Amz-Signature=" in signed


@override_settings(STORAGES=_OBJECT_STORAGE)
def test_the_url_is_identical_on_both_backends_for_the_same_key(client: Client) -> None:
    # "Backend-independent" stated directly: the stored row, the response, and the key
    # all agree, and the agreement is a pure function of the key rather than of who
    # stored it.
    url = _upload(client).json()["url"]

    upload = Upload.objects.get()
    assert upload.url == url
    key = served_object_key(url)
    assert key.startswith("uploads/")
    assert url == f"/media/{key}"
    assert default_storage.exists(key)


@override_settings(STORAGES=_OBJECT_STORAGE)
def test_the_minted_url_survives_a_round_trip_through_the_post_validator(
    client: Client,
) -> None:
    # Upload.url is copied verbatim into a Post/Product media_url — that is *why* an
    # expiring value was catastrophic rather than merely wrong.
    from apps.content.api import _validated_media_url

    url = _upload(client).json()["url"]

    assert _validated_media_url(url) == url


# --- what gets served ----------------------------------------------------------


@override_settings(STORAGES=_OBJECT_STORAGE)
def test_the_gated_view_serves_bytes_from_a_non_local_backend(client: Client) -> None:
    # Nothing about this backend is a filesystem, and the old view could only read one.
    url = _upload(client).json()["url"]

    res = client.get(url)

    assert res.status_code == 200
    assert res.streaming  # bytes are streamed, never buffered whole
    chunks = cast(StreamingHttpResponse, res).streaming_content
    assert b"".join(cast(Iterator[bytes], chunks)) == _BUCKET_OBJECTS[served_object_key(url)]


@override_settings(STORAGES=_OBJECT_STORAGE)
def test_served_headers_pin_the_type_and_forbid_sniffing(client: Client) -> None:
    res = client.get(_upload(client).json()["url"])

    assert res["Content-Type"] == "image/png"
    assert res["X-Content-Type-Options"] == "nosniff"
    assert res["Content-Disposition"] == "inline"
    # Gated media: a shared cache must never hold a copy that outlives a takedown.
    assert res["Cache-Control"] == "private, max-age=300"


@override_settings(STORAGES=_OBJECT_STORAGE)
def test_the_content_type_comes_from_the_row_not_the_key(client: Client) -> None:
    # WEBP is the case that proves the row is the authority: mimetypes does not know
    # ``.webp`` on this platform (see test_s3_hardening), so anything guessing from the
    # key's extension would serve application/octet-stream and the browser would
    # download the image instead of rendering it.
    url = _upload(client, WEBP, name="x.webp", content_type="image/webp").json()["url"]

    res = client.get(url)

    assert res.status_code == 200
    assert res["Content-Type"] == "image/webp"


def test_an_object_with_no_row_is_served_as_inert(client: Client) -> None:
    # Media predating the Upload table has no row to vouch for its type. It still
    # serves (no blanket 404s), but as the inert type rather than a guess — with nosniff
    # that is a download, never active content.
    name = default_storage.save("uploads/rowless.png", ContentFile(PNG))

    res = client.get(f"/media/{name}")

    assert res.status_code == 200
    assert res["Content-Type"] == "application/octet-stream"


# --- what does not get served --------------------------------------------------


@override_settings(STORAGES=_OBJECT_STORAGE)
def test_a_key_with_no_object_is_404_not_500(client: Client) -> None:
    # The view promises a body before it streams one; a missing object must be decided
    # before the 200, not raised half-way through it.
    assert client.get("/media/uploads/does-not-exist.png").status_code == 404


@override_settings(STORAGES=_OBJECT_STORAGE)
def test_the_quarantine_prefix_is_never_served(client: Client) -> None:
    key = "quarantine/uploads/hidden.png"
    default_storage.save(key, ContentFile(PNG))

    # 404, never 403: a distinguishable refusal would leak that a report exists.
    assert client.get(f"/media/{key}").status_code == 404


def test_a_traversal_key_is_refused(client: Client) -> None:
    # django.views.static.serve used to normalise the path for us; this view addresses
    # storage keys directly, so it refuses traversal itself. Asserted on the LOCAL
    # backend deliberately: that is where traversal means something, and where dropping
    # the guard would leave safe_join to raise (a 400 + a logged SuspiciousOperation)
    # instead of quietly 404ing a probe.
    assert client.get("/media/uploads/../../etc/passwd").status_code == 404
    assert client.get("/media/").status_code == 404


# --- the moderation round trip, on object storage -------------------------------


@override_settings(STORAGES=_OBJECT_STORAGE)
def test_upload_takedown_404_restore_200_round_trip(
    client: Client, django_capture_on_commit_callbacks: Any
) -> None:
    # Today's moderation contract, now asserted end-to-end on the backend production
    # actually runs — where the reads used to bypass Django entirely.
    operator = Account.objects.create(role=Role.OPERATOR.value)
    url = _upload(client).json()["url"]
    assert client.get(url).status_code == 200
    upload = Upload.objects.get()
    served_key = served_object_key(url)

    take_down_upload(upload=upload, actor=operator)

    assert client.get(url).status_code == 404
    upload.refresh_from_db()
    assert upload.status == UploadStatus.TAKEN_DOWN.value
    # Both halves agree: the row refuses, and the bytes are no longer at the key.
    assert not default_storage.exists(served_key)
    assert default_storage.exists(quarantine_key_for(served_key))

    with django_capture_on_commit_callbacks(execute=True):
        restore_upload(upload=upload, actor=operator)

    assert client.get(url).status_code == 200
    # The URL never changed across any of it — that is what "stable" buys.
    upload.refresh_from_db()
    assert upload.url == url


@override_settings(STORAGES=_OBJECT_STORAGE)
def test_a_taken_down_object_still_present_at_its_key_is_refused_by_the_row(
    client: Client,
) -> None:
    # The status check must stand on its own, not lean on the object having been moved:
    # it is what makes a takedown immediate on a read path Django serves. Here the row
    # says taken_down while the bytes are deliberately left at the served key.
    url = _upload(client).json()["url"]
    Upload.objects.update(status=UploadStatus.TAKEN_DOWN.value)

    assert default_storage.exists(served_object_key(url))
    assert client.get(url).status_code == 404


def test_serving_does_not_hold_the_object_open(client: Client) -> None:
    # Windows regression: a response that opens the file eagerly keeps a handle on it,
    # and a takedown's move then fails outright. The view opens nothing until the body
    # is pulled, so a caller that reads only status/headers — and never closes the
    # response — cannot block moderation.
    operator = Account.objects.create(role=Role.OPERATOR.value)
    url = _upload(client).json()["url"]

    assert client.get(url).status_code == 200  # deliberately not closed
    take_down_upload(upload=Upload.objects.get(), actor=operator)

    assert not default_storage.exists(served_object_key(url))
