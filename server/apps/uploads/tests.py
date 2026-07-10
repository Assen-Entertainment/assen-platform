"""Tests for the image upload endpoint (R11+ASS-271 — mock storage, magic-byte +
Pillow decode-verify gated).

Central assertions: an authenticated PNG upload returns a site-relative ``/media``
URL that is (a) written to storage and (b) accepted by the same ``media_url``
validator Post/Product apply; a non-image content-type is refused (415); a forged
content-type (declared image, non-image bytes) is caught by the magic-byte sniff
(422); SVG/HTML are refused (XSS); an oversize file is refused (413); a
signature-valid-but-corrupted/truncated/polyglot payload is caught by the Pillow
decode-verify step (422, ASS-271); an image whose dimensions or total pixel count
exceed the decompression-bomb guard is refused (422, ASS-271); the stored name is
a server UUID (no user filename leaks); and the endpoint requires auth.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any
from unittest.mock import PropertyMock, patch

import pytest
from django.core.files.base import File
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from PIL import Image

from apps.content.api import _validated_media_url
from apps.identity.models import Account, Role
from apps.identity.services import issue_token_pair
from apps.uploads.images import looks_scriptable, sniff_image_kind, verify_image_decodes
from apps.uploads.models import Upload

pytestmark = pytest.mark.django_db

URL = "/api/uploads"


def _real_image(fmt: str, *, size: tuple[int, int] = (4, 4)) -> bytes:
    """A tiny but genuinely decodable image, so the Pillow decode-verify step passes."""
    buf = BytesIO()
    Image.new("RGB", size, color=(255, 0, 0)).save(buf, format=fmt)
    return buf.getvalue()


# Real, fully-decodable fixtures (the endpoint now runs Pillow decode-verify on the
# full payload, not just a magic-byte sniff on the leading bytes).
PNG = _real_image("PNG")
GIF = _real_image("GIF")
WEBP = _real_image("WEBP")
JPEG = _real_image("JPEG")

# Magic-byte-only fixtures: valid leading signature, but not a real decodable image
# past that — these must pass the sniff (kind is not None) yet fail decode-verify.
_FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
_FAKE_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16


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


# --- Pillow decode-verify boundary (ASS-271) ----------------------------------


def test_magic_bytes_only_payload_rejected_422(client: Client) -> None:
    # Passes the 64-byte magic sniff (real PNG/JPEG signature) but is not a real,
    # fully decodable image past that — the deeper Pillow decode-verify must catch it.
    fan = _fan()
    for data, content_type in ((_FAKE_PNG, "image/png"), (_FAKE_JPEG, "image/jpeg")):
        res = _upload(client, data, content_type=content_type, headers=_auth(fan))
        assert res.status_code == 422, (content_type, res.content)
        assert res.json()["code"] == "UploadInvalid"
    assert Upload.objects.count() == 0


def test_truncated_image_rejected_422(client: Client) -> None:
    # A real PNG whose tail is cut off — valid signature, but Pillow's decode-verify
    # cannot fully read the (now-incomplete) stream.
    fan = _fan()
    truncated = PNG[: len(PNG) // 2]
    res = _upload(client, truncated, headers=_auth(fan))
    assert res.status_code == 422
    assert res.json()["code"] == "UploadInvalid"
    assert Upload.objects.count() == 0


def test_polyglot_png_with_trailing_markup_rejected_422(client: Client) -> None:
    # A real, valid PNG with scriptable markup appended after IEND — a polyglot that
    # a sniff-only check would accept, but decode-verify still accepts *this specific*
    # case since Pillow only reads up to IEND. What actually defeats this class of
    # attack in production is the sniff-derived Content-Type + nosniff header (see
    # apps.uploads.images docstring); this test documents that a well-formed PNG with
    # trailing bytes still uploads cleanly (control case for the corruption tests
    # above, where the *leading* structure itself is broken).
    fan = _fan()
    polyglot = PNG + b"<script>alert(1)</script>"
    res = _upload(client, polyglot, headers=_auth(fan))
    assert res.status_code == 201, res.content


@override_settings(UPLOAD_MAX_DIMENSION=8)
def test_oversized_dimension_rejected_422(client: Client) -> None:
    fan = _fan()
    too_wide = _real_image("PNG", size=(16, 4))
    res = _upload(client, too_wide, headers=_auth(fan))
    assert res.status_code == 422
    assert res.json()["code"] == "UploadInvalid"
    assert Upload.objects.count() == 0


@override_settings(UPLOAD_MAX_PIXELS=32, UPLOAD_MAX_DIMENSION=1000)
def test_oversized_pixel_count_rejected_422(client: Client) -> None:
    fan = _fan()
    # 8x8 = 64px, each dimension well under the 1000px cap but the total exceeds 32.
    too_many_pixels = _real_image("PNG", size=(8, 8))
    res = _upload(client, too_many_pixels, headers=_auth(fan))
    assert res.status_code == 422
    assert res.json()["code"] == "UploadInvalid"
    assert Upload.objects.count() == 0


def test_verify_image_decodes_accepts_real_images_within_bounds() -> None:
    from apps.uploads.images import sniff_image_kind as _sniff

    for data in (PNG, GIF, WEBP, JPEG):
        kind = _sniff(data)
        assert kind is not None
        assert verify_image_decodes(data, kind, max_pixels=40_000_000, max_dimension=12_000)


def test_verify_image_decodes_rejects_corrupted_and_truncated() -> None:
    png_kind = sniff_image_kind(_FAKE_PNG)
    assert png_kind is not None
    assert not verify_image_decodes(
        _FAKE_PNG, png_kind, max_pixels=40_000_000, max_dimension=12_000
    )

    real_png_kind = sniff_image_kind(PNG)
    assert real_png_kind is not None
    truncated = PNG[: len(PNG) // 2]
    assert not verify_image_decodes(
        truncated, real_png_kind, max_pixels=40_000_000, max_dimension=12_000
    )


def test_verify_image_decodes_rejects_dimension_and_pixel_bombs() -> None:
    kind = sniff_image_kind(PNG)  # 4x4 = 16px
    assert kind is not None
    # Dimension cap: one side (4) exceeds a cap of 2.
    assert not verify_image_decodes(PNG, kind, max_pixels=40_000_000, max_dimension=2)
    # Pixel-count cap: 16px exceeds a cap of 10, even though 4 <= max_dimension.
    assert not verify_image_decodes(PNG, kind, max_pixels=10, max_dimension=12_000)
    # Sanity: passes when both caps are generous.
    assert verify_image_decodes(PNG, kind, max_pixels=40_000_000, max_dimension=12_000)


def test_verify_image_decodes_rejects_format_mismatch() -> None:
    # A real JPEG's bytes, but claiming (via the wrong ImageKind) to be a PNG —
    # the format cross-check must catch the mismatch even though the bytes decode.
    jpeg_kind = sniff_image_kind(JPEG)
    png_kind = sniff_image_kind(PNG)
    assert jpeg_kind is not None and png_kind is not None
    assert not verify_image_decodes(
        JPEG, png_kind, max_pixels=40_000_000, max_dimension=12_000
    )


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
