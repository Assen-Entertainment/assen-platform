"""Object-storage hardening: what a stored object's response headers will be (gate #2).

A stored image must never be serveable as an executable/HTML type. That is enforced
by the write parameters django-storages sends to S3, which come from two places that
are easy to get wrong independently:

- ``object_parameters`` (config.settings.base) — applied **verbatim to every object**,
  so it can only carry values uniform across all four raster families. That rules out
  ContentType: pinning one there would stamp e.g. image/png onto a JPEG.
- the write site (apps.uploads.api) — pins the per-object ContentType from the
  magic-byte sniff, never the client's claim.

These tests assert the composed result, because neither half is correct alone. They
drive django-storages' real parameter builder with no bucket/network involved.

The regression that motivates the ContentType pin specifically: ``mimetypes`` does not
know ``.webp`` on every platform (it returns None on this one), so without the pin the
backend's own extension-guess fallback would store every WEBP as
application/octet-stream — downloading instead of rendering.
"""

from __future__ import annotations

import mimetypes
from io import BytesIO
from typing import Any

import pytest
from django.core.files.base import ContentFile
from PIL import Image
from storages.backends.s3 import S3Storage

from apps.uploads.images import ImageKind, sniff_image_kind

# The OPTIONS block config.settings.base builds when DJANGO_MEDIA_S3_BUCKET is set.
# Mirrored (not imported) so a change to the settings hardening has to be a deliberate
# edit here too, rather than silently redefining what this file claims to protect.
_OPTIONS: dict[str, Any] = {
    "bucket_name": "assen-media-test",
    "default_acl": None,
    "querystring_auth": True,
    "file_overwrite": False,
    "signature_version": "s3v4",
    "object_parameters": {
        "ContentDisposition": "inline",
        "CacheControl": "private, max-age=300",
    },
}


def _storage() -> S3Storage:
    return S3Storage(**_OPTIONS)


def _sniffed(pillow_format: str) -> ImageKind:
    """The ImageKind the endpoint would derive from a real image of this format.

    Derived by sniffing genuine bytes rather than hand-building an ImageKind, so these
    are exactly the values production pins.
    """
    buf = BytesIO()
    Image.new("RGB", (4, 4), color=(0, 128, 255)).save(buf, format=pillow_format)
    kind = sniff_image_kind(buf.getvalue())
    assert kind is not None
    return kind


def _write_params(kind: ImageKind) -> dict[str, Any]:
    """The parameters S3 would receive for an upload of this sniffed kind."""
    content = ContentFile(b"pixels")
    # Exactly what apps.uploads.api does before default_storage.save().
    content.content_type = kind.content_type  # type: ignore[attr-defined]
    name = f"uploads/deadbeef.{kind.extension}"
    return dict(_storage()._get_write_parameters(name, content))


@pytest.mark.parametrize(
    "pillow_format,expected_content_type",
    [
        ("PNG", "image/png"),
        ("JPEG", "image/jpeg"),
        ("GIF", "image/gif"),
        ("WEBP", "image/webp"),
    ],
)
def test_stored_object_gets_its_own_sniffed_image_content_type(
    pillow_format: str, expected_content_type: str
) -> None:
    params = _write_params(_sniffed(pillow_format))
    assert params["ContentType"] == expected_content_type


def test_stored_object_is_never_disposed_as_active_content() -> None:
    params = _write_params(_sniffed("PNG"))
    # inline (not attachment): these are feed images and must render. Safety comes
    # from the forced image/* ContentType above + the global nosniff header, not from
    # forcing a download.
    assert params["ContentDisposition"] == "inline"


def test_private_objects_are_not_shared_cached() -> None:
    # The signed URL is the capability; a shared proxy cache would serve the bytes to
    # a caller whose own signature had already expired.
    params = _write_params(_sniffed("PNG"))
    assert params["CacheControl"] == "private, max-age=300"


def test_no_acl_is_sent_so_the_bucket_stays_private() -> None:
    params = _write_params(_sniffed("PNG"))
    assert "ACL" not in params


def test_content_type_pin_is_load_bearing_for_webp() -> None:
    # Documents *why* the write site pins the type rather than trusting the backend's
    # extension guess. If this ever starts passing (mimetypes learns webp), the pin is
    # still correct — it just stops being the only thing standing between a WEBP
    # upload and an application/octet-stream that browsers download instead of render.
    assert mimetypes.guess_type("x.webp") == (None, None)

    unpinned = ContentFile(b"pixels")
    params = _storage()._get_write_parameters("uploads/deadbeef.webp", unpinned)
    assert params["ContentType"] == "application/octet-stream"
    # Whatever the fallback is, it must at minimum never be active content.
    assert params["ContentType"] not in {"text/html", "application/javascript"}
