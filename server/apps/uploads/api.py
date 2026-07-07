"""Image upload endpoint (R11 — mock local storage, magic-byte validated).

``POST /api/uploads`` (``fan_auth`` — unauthenticated → 401): accepts a single
multipart image and returns ``{"url": "/media/uploads/<uuid>.<ext>"}``. That URL
is a drop-in ``media_url`` for a Post/Product/avatar (it passes the same
``_validated_media_url`` those endpoints apply).

Fail-closed availability: no real object-storage backend is wired yet, so the
endpoint only accepts writes where the stored bytes are also served locally
(``settings.SERVE_LOCAL_MEDIA`` — dev/test/demo). With that off (prod) it returns
503 rather than write to a local disk nothing can serve (un-renderable objects +
disk-exhaustion risk).

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
- the stored filename is a server-minted UUID (never the user's) written under a
  non-executable ``uploads/`` prefix — path traversal and PII are impossible;
- the stored content-type/extension come from the sniff, never the client.

Real object moderation (nudity/abuse scanning), a full magic-byte decode
(Pillow verify + decompression-bomb guard), and a real S3 backend are 후행 (see the
moderation hook below and ``config.settings.base`` STORAGES plugin point, which
lists the required gates before a real serving path).
"""

from __future__ import annotations

import uuid
from typing import Annotated, cast

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import HttpRequest
from ninja import File, Router, Schema
from ninja.files import UploadedFile

from apps.identity.auth import fan_auth
from apps.identity.models import Account
from apps.uploads.images import (
    ALLOWED_CONTENT_TYPES,
    ImageKind,
    looks_scriptable,
    sniff_image_kind,
)
from apps.uploads.models import Upload
from config.api import api
from config.errors import ApiError, ErrorCode
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


def _moderation_accepts(data: bytes) -> bool:
    """Mock content-moderation hook — accepts every (already image-validated) file.

    Real moderation (nudity/abuse/CSAM scanning via a provider or Rekognition) is a
    separate 대표·법무 gate — HUMAN-REVIEW-REQUIRED, and one of the required gates
    before a real (non-demo) media-serving path (see ``config.settings.base``
    STORAGES). When wired it replaces this stub, returning False (→ 422) for a
    rejected object. The stub accepts so the upload flow can be exercised end to end;
    it never inspects PII.
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
    :data:`~django.conf.settings.UPLOAD_MAX_BYTES` (413), or bytes that are not a
    real allowed image / are scriptable markup (422). On success writes the bytes
    under a UUID name via the storage backend and records an :class:`Upload` row.
    """
    # 0) Fail closed unless this environment also serves the stored bytes (there is
    # no real object-storage backend yet). Off (prod) → refuse rather than write to a
    # local disk nothing can serve (un-renderable objects + disk-exhaustion risk).
    if not settings.SERVE_LOCAL_MEDIA:
        raise ApiError(
            503,
            "업로드가 아직 준비되지 않았어요.",
            code=ErrorCode.UPLOAD_STORAGE_UNAVAILABLE,
        )

    account = cast(Account, request.auth)  # type: ignore[attr-defined]

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

    # 5) Mock moderation hook (real provider is 후행 — see _moderation_accepts).
    if not _moderation_accepts(data):
        raise ApiError(
            422, "업로드가 거부됐어요.", code=ErrorCode.UPLOAD_INVALID
        )

    # 6) Store under a server-minted UUID name (never the user's filename → no path
    # traversal / PII) with the sniffed extension, via the storage abstraction.
    object_name = f"uploads/{uuid.uuid4().hex}.{kind.extension}"
    stored_name = default_storage.save(object_name, ContentFile(data))
    url = default_storage.url(stored_name)

    Upload.objects.create(owner=account, url=url, content_type=kind.content_type)
    return 201, UploadOut(url=url)


api.add_router("/uploads", uploads_router)
