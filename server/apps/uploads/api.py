"""Image upload endpoint (R11 — mock local storage, magic-byte validated).

``POST /api/uploads`` (``fan_auth`` — unauthenticated → 401): accepts a single
multipart image and returns ``{"url": "/media/uploads/<uuid>.<ext>"}``. That URL
is a drop-in ``media_url`` for a Post/Product/avatar (it passes the same
``_validated_media_url`` those endpoints apply).

Security boundary (see also :mod:`apps.uploads.images`):
- content-type whitelist (415) — declared type must be an allowed raster family;
- magic-byte sniff (422) — the *bytes* must actually be that image, defeating a
  forged content-type / renamed extension;
- SVG/HTML/script markup refused (422 / 415) — no active content that could XSS;
- size ceiling (413) — enforced from ``file.size`` before the bytes are read;
- the stored filename is a server-minted UUID (never the user's) written under a
  non-executable ``uploads/`` prefix — path traversal and PII are impossible;
- the stored content-type/extension come from the sniff, never the client.

Real object moderation (nudity/abuse scanning) and a real S3 backend are 후행
(see the moderation hook below and ``config.settings.base`` STORAGES plugin point).
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


class UploadOut(Schema):
    """The stored object's site-relative media URL (drop-in for a ``media_url``)."""

    url: str


class UploadError(Schema):
    """Stable ``{detail, code}`` error shape for the upload endpoint."""

    detail: str
    code: str


def _moderation_accepts(data: bytes) -> bool:
    """Mock content-moderation hook — accepts every (already image-validated) file.

    Real moderation (nudity/abuse/CSAM scanning via a provider or Rekognition) is a
    separate 대표·법무 gate — HUMAN-REVIEW-REQUIRED. When wired it replaces this stub,
    returning False (→ 422) for a rejected object. The stub accepts so the upload
    flow can be exercised end to end; it never inspects PII.
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

    Rejects (coded ``ApiError``): a non-image declared content-type (415), a file
    over :data:`~django.conf.settings.UPLOAD_MAX_BYTES` (413), or bytes that are not
    a real allowed image / are scriptable markup (422). On success writes the bytes
    under a UUID name via the storage backend and records an :class:`Upload` row.
    """
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

    # 2) Size ceiling — checked from the reported size BEFORE reading the bytes so an
    # oversize upload never lands in memory or storage.
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

    # 4) Read the full payload (guarded again in case the reported size lied).
    data = file.read()
    if len(data) > max_bytes:
        raise ApiError(
            413, "파일이 너무 커요.", code=ErrorCode.UPLOAD_TOO_LARGE
        )

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
