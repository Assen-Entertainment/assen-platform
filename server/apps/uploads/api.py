"""Image upload endpoint (magic-byte + Pillow validated, report-moderated).

``POST /api/uploads`` (``fan_auth`` — unauthenticated → 401): accepts a single
multipart image and returns ``{"url": "/media/uploads/<uuid>.<ext>"}``. That URL
is a drop-in ``media_url`` for a Post/Product/avatar (it passes the same
``_validated_media_url`` those endpoints apply).

Fail-closed availability (:func:`uploads_enabled`): the endpoint accepts writes only
when ``settings.ALLOW_UPLOADS`` is on AND the storage backend is usable
(``config.storage.media_storage_ready``). Otherwise 503.

The returned URL is **stable and backend-independent** — ``{MEDIA_URL}uploads/<uuid>.
<ext>``, minted from the storage key by ``apps.uploads.services.media_url_for_key``,
identical on the local filesystem and on S3. It is deliberately NOT
``default_storage.url()``: on S3 with ``querystring_auth`` that returns a *signed URL
that expires in an hour*, and this value is persisted on the row and copied verbatim
into a Post/Product ``media_url`` — so minting one would break every production image
about an hour after upload. Django serves the bytes back at that URL on every backend
(apps.uploads.media), which is also what makes a takedown immediate.

Moderation posture (대표 approved 07-18): report-driven human moderation. Bytes are
accepted once they pass the hard image validation below, are reportable via
``apps.safety`` (report intake takes an ``upload_id``), and an operator taking such a
report to ``actioned`` takes the image down — after which the media route stops
serving it. Automated provider scanning is 후행 (see ``_moderation_accepts``).

Security boundary (see also :mod:`apps.uploads.images`):
- content-type whitelist (415) — declared type must be an allowed raster family;
- magic-byte sniff (422) — the *bytes* must actually be that image, defeating a
  forged content-type / renamed extension. This is the primary control together
  with the sniff-derived stored content-type + a global nosniff header; the
  scriptable-markup scan is secondary defence-in-depth;
- SVG/HTML/script markup refused (422 / 415) — no active content that could XSS;
- size ceiling (413) — a reported ``file.size`` over the limit is refused before
  any bytes are read; an absent or lying size is still bounded because the payload
  is read in fixed chunks that abort the instant the accumulated length crosses
  the ceiling (so oversize bytes never accumulate unbounded in memory);
- Pillow decode-verify (422, ASS-271) — once the full payload is read, it must
  actually decode as the sniffed image family (``Image.open(...).verify()``),
  catching truncated/corrupted/polyglot files that pass the 64-byte magic sniff,
  plus an ``UPLOAD_MAX_PIXELS``/``UPLOAD_MAX_DIMENSION`` decompression-bomb guard;
- the stored filename is a server-minted UUID (never the user's) written under a
  non-executable ``uploads/`` prefix — path traversal and PII are impossible;
- the stored content-type/extension come from the sniff, never the client.

``config.settings.base`` STORAGES documents the full gate list and which are met.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import HttpRequest
from ninja import File, Router, Schema
from ninja.files import UploadedFile

from apps.identity.auth import authed, fan_auth
from apps.uploads.images import (
    ALLOWED_CONTENT_TYPES,
    ImageKind,
    looks_scriptable,
    sniff_image_kind,
    strip_metadata,
    verify_image_decodes,
)
from apps.uploads.models import Upload
from apps.uploads.services import media_url_for_key
from config.api import api
from config.errors import ApiError, ErrorCode
from config.storage import media_storage_ready
from config.throttle import user_write_throttle

uploads_router = Router(auth=fan_auth, tags=["uploads"])

# Bytes read from the head for magic-number sniffing + the scriptable-markup scan.
# 64 comfortably covers every signature we check (WEBP needs the first 12 bytes).
_SNIFF_BYTES = 64

# Chunk size for the bounded full-payload read (step 4). Reading in fixed chunks and
# aborting the moment the running total crosses UPLOAD_MAX_BYTES caps peak memory at
# ~ceiling + one chunk, independent of whether the client reported a size.
_READ_CHUNK_BYTES = 64 * 1024


class UploadOut(Schema):
    """The stored object's site-relative media URL (drop-in for a ``media_url``)."""

    url: str


def uploads_enabled() -> bool:
    """Whether this environment may accept an upload at all.

    Two independent conditions, both required:

    - ``ALLOW_UPLOADS`` — the deliberate decision to take untrusted bytes here
      (env-driven, fail-closed by default).
    - the storage backend can actually hold the object
      (:func:`~config.storage.media_storage_ready`).

    The second condition is the original bug preserved as an invariant: accepting an
    upload that cannot come back leaves un-renderable objects behind and turns the
    endpoint into a disk-exhaustion vector. It used to also ask "can anything serve
    this?", which is no longer a question — Django serves media itself on every backend
    (apps.uploads.media), so only the store's own usability is still in doubt.
    """
    if not settings.ALLOW_UPLOADS:
        return False
    return media_storage_ready()


def _moderation_accepts(data: bytes) -> bool:
    """Automated content-scan seam — currently accepts every image-validated file.

    **This is no longer the moderation gate.** The platform's moderation posture is
    report-driven human moderation (대표 approved 07-18): an accepted image is
    reportable through the safety domain (``apps.safety`` — the fan/operator report
    intake takes an ``upload_id``), and an operator taking that report to ``actioned``
    takes the image down so it stops being served
    (``apps.uploads.services.take_down_upload``). That is what makes accepting uploads
    defensible today.

    This hook remains the plug-in point for *automated* pre-publication scanning
    (nudity/CSAM via a provider — Rekognition et al.), which is still 후행 and still a
    대표·법무 gate. When wired it returns False (→ 422) for a rejected object, adding a
    machine filter in front of the human one rather than replacing it. It never
    inspects PII.
    """
    del data
    return True


@uploads_router.post(
    "",
    response={201: UploadOut},
    throttle=user_write_throttle("30/min"),
)
def create_upload(
    request: HttpRequest, file: Annotated[UploadedFile, File(...)]
) -> tuple[int, UploadOut]:
    """Validate + store a single uploaded image; return its media URL.

    Rejects (coded ``ApiError``): the upload surface being fail-closed off (503,
    no serving backend wired), a non-image declared content-type (415), a file over
    :data:`~django.conf.settings.UPLOAD_MAX_BYTES` (413), bytes that are not a real
    allowed image / are scriptable markup (422), or bytes that pass the magic-byte
    sniff but fail Pillow's full decode-verify / exceed the pixel-count or
    dimension bomb guard (422). On success writes the bytes under a UUID name via
    the storage backend and records an :class:`Upload` row.
    """
    # 0) Fail closed unless this environment both allows uploads and has some way to
    # serve them back (see uploads_enabled). Refusing here beats writing bytes nothing
    # can render (un-renderable objects + disk-exhaustion risk).
    if not uploads_enabled():
        raise ApiError(
            503,
            "업로드가 아직 준비되지 않았어요.",
            code=ErrorCode.UPLOAD_STORAGE_UNAVAILABLE,
        )

    account = authed(request)

    # 1) Coarse gate: the declared content-type must be an allowed raster family.
    # This is spoofable, so it is only the first filter (SVG/HTML declared honestly
    # are refused here); the magic-byte sniff below is the authoritative check.
    if (file.content_type or "") not in ALLOWED_CONTENT_TYPES:
        raise ApiError(
            415,
            "이미지 파일(PNG/JPEG/WEBP/GIF)만 업로드할 수 있어요.",
            code=ErrorCode.UPLOAD_TYPE_UNSUPPORTED,
        )

    # 2) Size ceiling (fast path) — if the client reported a size over the limit,
    # refuse before reading any bytes. A reported size can be absent or lie, so this
    # is only an early-out; step 4 re-enforces the ceiling on the bytes actually read.
    max_bytes = settings.UPLOAD_MAX_BYTES
    if file.size is not None and file.size > max_bytes:
        raise ApiError(
            413, "파일이 너무 커요.", code=ErrorCode.UPLOAD_TOO_LARGE
        )

    # 3) Sniff the real type from the leading bytes; reject scriptable markup and
    # anything that is not one of the four allowed raster formats.
    head = file.read(_SNIFF_BYTES)
    file.seek(0)
    if looks_scriptable(head):
        raise ApiError(
            422, "허용되지 않는 파일이에요.", code=ErrorCode.UPLOAD_INVALID
        )
    kind: ImageKind | None = sniff_image_kind(head)
    if kind is None:
        raise ApiError(
            422, "이미지 파일이 아니에요.", code=ErrorCode.UPLOAD_INVALID
        )

    # 4) Read the full payload in bounded chunks, aborting with 413 the instant the
    # accumulated length crosses the ceiling. This holds regardless of whether the
    # reported size was absent or lied, and caps peak memory at ~ceiling + one chunk
    # (never the whole oversize body). The head sniff above left the cursor at 0.
    # (A body-size cap at the ingress/ALB layer is a complementary deployment-level
    # guard; this is the application-level ceiling.)
    file.seek(0)
    parts: list[bytes] = []
    total = 0
    while True:
        chunk = file.read(_READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ApiError(
                413, "파일이 너무 커요.", code=ErrorCode.UPLOAD_TOO_LARGE
            )
        parts.append(chunk)
    data = b"".join(parts)

    # 5) Full Pillow decode-verify (ASS-271) on the complete payload: the sniff above
    # only inspected the leading 64 bytes, so a truncated/corrupted/polyglot file can
    # still carry a valid magic number. This also enforces the decompression-bomb /
    # dimension guards before any pixel data is decoded further downstream.
    if not verify_image_decodes(
        data,
        kind,
        max_pixels=settings.UPLOAD_MAX_PIXELS,
        max_dimension=settings.UPLOAD_MAX_DIMENSION,
    ):
        raise ApiError(
            422, "이미지 파일이 아니에요.", code=ErrorCode.UPLOAD_INVALID
        )

    # 6) Mock moderation hook (real provider is 후행 — see _moderation_accepts).
    if not _moderation_accepts(data):
        raise ApiError(
            422, "업로드가 거부됐어요.", code=ErrorCode.UPLOAD_INVALID
        )

    # 7) Strip ALL metadata (EXIF/XMP/GPS/ICC — e.g. an embedded phone number or GPS
    # location) by canonically re-encoding through Pillow in the sniffed format
    # (ASS-293). verify_image_decodes only decode-verifies; without this the original
    # bytes — metadata and all — would be stored and served. The image is already
    # dimension/pixel-capped (step 5), so this full re-decode is not a bomb. A
    # re-encode failure on a payload that passed decode-verify is treated as an
    # unusable image (422), keeping the endpoint fail-closed rather than raising 500.
    try:
        data = strip_metadata(data, kind)
    except Exception as exc:
        raise ApiError(
            422, "이미지 파일이 아니에요.", code=ErrorCode.UPLOAD_INVALID
        ) from exc

    # 8) Store under a server-minted UUID name (never the user's filename → no path
    # traversal / PII) with the sniffed extension, via the storage abstraction.
    # NOTE: the multipart parser reads the whole request body before the size ceiling
    # (steps 2/4) can reject it — a true early *ingress* byte cap is a reverse-proxy /
    # deployment concern (nginx client_max_body_size / ALB), not fixable in-app here.
    object_name = f"uploads/{uuid.uuid4().hex}.{kind.extension}"
    content = ContentFile(data)
    # Pin the stored object's Content-Type to the SNIFFED type (never the client's
    # declared one). django-storages' S3 backend reads ``content.content_type`` when
    # writing (S3Storage._get_write_parameters) — it cannot come from the settings'
    # object_parameters, which are applied verbatim to every object and so cannot vary
    # per image family (see config.settings.base). Without this the backend would fall
    # back to guessing from the key's extension, which is sniff-derived and therefore
    # correct, but relies on the runtime mimetypes registry knowing every family
    # (webp is absent on some platforms) — pinning it removes that dependency.
    # FileSystemStorage ignores the attribute, so dev/test behaviour is unchanged.
    content.content_type = kind.content_type  # type: ignore[attr-defined]
    stored_name = default_storage.save(object_name, content)
    # 9) Mint the URL from the KEY the backend actually stored under (save() may rename
    # on collision), never from default_storage.url(): that is signed and expiring on
    # S3, and this string is persisted + copied into Post/Product media_url, so it must
    # not have a lifetime. media_url_for_key is the exact inverse of the served_object_key
    # a takedown moves — one scheme, both backends (apps.uploads.services).
    url = media_url_for_key(stored_name)

    Upload.objects.create(owner=account, url=url, content_type=kind.content_type)
    return 201, UploadOut(url=url)


api.add_router("/uploads", uploads_router)
