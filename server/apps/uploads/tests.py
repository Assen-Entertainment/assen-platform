"""Tests for the image upload endpoint (R11 — mock storage, magic-byte gated).

Central assertions: an authenticated PNG upload returns a site-relative ``/media``
URL that is (a) written to storage and (b) accepted by the same ``media_url``
validator Post/Product apply; a non-image content-type is refused (415); a forged
content-type (declared image, non-image bytes) is caught by the magic-byte sniff
(422); SVG/HTML are refused (XSS); an oversize file is refused (413); the stored
name is a server UUID (no user filename leaks); and the endpoint requires auth.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import PropertyMock, patch

import pytest
from django.core.files.base import File
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings

from apps.content.api import _validated_media_url
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.uploads.images import looks_scriptable, sniff_image_kind
from apps.uploads.models import Upload

pytestmark = pytest.mark.django_db

URL = "/api/uploads"

# Minimal fixtures carrying valid leading magic bytes (the endpoint never decodes
# the raster body, only sniffs the signature).
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
GIF = b"GIF89a" + b"\x00" * 16
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 16
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16


def _fan() -> Account:
    return Account.objects.create(role=Role.FAN.value)


def _auth(account: Account) -> dict[str, str]:
    return {"authorization": f"Bearer {issue_token_pair(account).access_token}"}


def _upload(
    client: Client,
    data: bytes,
    *,
    name: str = "x.png",
    content_type: str = "image/png",
    headers: dict[str, str] | None = None,
) -> Any:
    upload = SimpleUploadedFile(name, data, content_type=content_type)
    return client.post(URL, {"file": upload}, headers=headers or {})


def test_requires_auth_401(client: Client) -> None:
    upload = SimpleUploadedFile("x.png", PNG, content_type="image/png")
    assert client.post(URL, {"file": upload}).status_code in {401, 403}


def test_png_upload_returns_media_url_and_saves(client: Client) -> None:
    fan = _fan()
    res = _upload(client, PNG, headers=_auth(fan))
    assert res.status_code == 201, res.content
    url = res.json()["url"]
    # Site-relative /media URL with a server-minted UUID name + sniffed extension.
    assert url.startswith("/media/uploads/")
    assert url.endswith(".png")
    assert "x.png" not in url  # the user filename never appears
    # Accepted verbatim by the shared media_url validator (Post/Product reuse it).
    assert _validated_media_url(url) == url
    # A row tracks the upload (owner + sniffed content-type), and the bytes exist.
    up = Upload.objects.get(owner=fan)
    assert up.content_type == "image/png"
    assert up.url == url
    stored_name = url.split("/media/", 1)[1]
    assert default_storage.exists(stored_name)


def test_gif_webp_jpeg_accepted(client: Client) -> None:
    fan = _fan()
    cases = (
        (GIF, "image/gif", ".gif"),
        (WEBP, "image/webp", ".webp"),
        (JPEG, "image/jpeg", ".jpg"),
    )
    for data, content_type, ext in cases:
        res = _upload(client, data, content_type=content_type, headers=_auth(fan))
        assert res.status_code == 201, (content_type, res.content)
        assert res.json()["url"].endswith(ext)


def test_non_image_content_type_rejected_415(client: Client) -> None:
    fan = _fan()
    res = _upload(
        client, b"hello world", name="x.txt", content_type="text/plain", headers=_auth(fan)
    )
    assert res.status_code == 415
    assert res.json()["code"] == "UploadTypeUnsupported"
    assert Upload.objects.count() == 0


def test_forged_content_type_rejected_by_magic_bytes_422(client: Client) -> None:
    fan = _fan()
    # Declares image/png (passes the coarse gate) but the bytes are not an image.
    res = _upload(client, b"this is definitely not a png", headers=_auth(fan))
    assert res.status_code == 422
    assert res.json()["code"] == "UploadInvalid"
    assert Upload.objects.count() == 0


def test_svg_rejected(client: Client) -> None:
    fan = _fan()
    svg = b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>"
    # Honestly declared SVG → not in the image whitelist → 415.
    declared = _upload(client, svg, name="x.svg", content_type="image/svg+xml", headers=_auth(fan))
    assert declared.status_code == 415
    # Disguised as PNG → scriptable/magic sniff catches it → 422.
    disguised = _upload(client, svg, headers=_auth(fan))
    assert disguised.status_code == 422
    assert disguised.json()["code"] == "UploadInvalid"
    assert Upload.objects.count() == 0


def test_html_rejected_415(client: Client) -> None:
    fan = _fan()
    html = b"<!doctype html><html><body><script>alert(1)</script></body></html>"
    res = _upload(client, html, name="x.html", content_type="text/html", headers=_auth(fan))
    assert res.status_code == 415


@override_settings(UPLOAD_MAX_BYTES=16)
def test_oversize_rejected_413(client: Client) -> None:
    fan = _fan()
    big = PNG + b"\x00" * 4096  # far exceeds the 16-byte test ceiling
    res = _upload(client, big, headers=_auth(fan))
    assert res.status_code == 413
    assert res.json()["code"] == "UploadTooLarge"
    assert Upload.objects.count() == 0


@override_settings(UPLOAD_MAX_BYTES=16)
def test_oversize_via_chunk_path_when_size_unknown_413(client: Client) -> None:
    # When the reported size is absent (file.size is None) the step-2 fast path is
    # skipped, so the bounded chunk read must still abort the oversize payload.
    fan = _fan()
    big = PNG + b"\x00" * 4096
    with patch.object(File, "size", new_callable=PropertyMock, return_value=None):
        res = _upload(client, big, headers=_auth(fan))
    assert res.status_code == 413
    assert res.json()["code"] == "UploadTooLarge"
    assert Upload.objects.count() == 0


@override_settings(SERVE_LOCAL_MEDIA=False)
def test_upload_disabled_when_storage_unavailable_503(client: Client) -> None:
    # Fail closed: with no local serving (and no real object store wired) the endpoint
    # refuses rather than write bytes nothing can serve. Valid PNG still gets a 503.
    fan = _fan()
    res = _upload(client, PNG, headers=_auth(fan))
    assert res.status_code == 503
    assert res.json()["code"] == "UploadStorageUnavailable"
    assert Upload.objects.count() == 0


# --- pure image-sniff unit tests (no HTTP) ------------------------------------


def test_sniff_detects_each_family() -> None:
    cases = (
        (PNG, "image/png"),
        (GIF, "image/gif"),
        (WEBP, "image/webp"),
        (JPEG, "image/jpeg"),
    )
    for data, expected in cases:
        kind = sniff_image_kind(data)
        assert kind is not None and kind.content_type == expected
    assert sniff_image_kind(b"not an image at all") is None


def test_looks_scriptable_flags_markup() -> None:
    assert looks_scriptable(b"<svg xmlns='...'>")
    assert looks_scriptable(b"  <!DOCTYPE html>")
    assert looks_scriptable(b"<?xml version='1.0'?>")
    assert not looks_scriptable(PNG)
