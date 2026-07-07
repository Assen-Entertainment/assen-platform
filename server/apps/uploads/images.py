"""Magic-byte image validation for uploaded media (the upload security boundary).

The client-declared multipart ``Content-Type`` is trivially spoofable, so it is
only a coarse first gate (:data:`ALLOWED_CONTENT_TYPES`). The authoritative check
is :func:`sniff_image_kind`, which inspects the file's leading bytes (magic
numbers) and returns the image family the bytes *actually are* — or ``None`` for
anything that is not one of the four allowed raster formats. That is what defeats
an attacker renaming ``payload.svg`` to ``avatar.png`` / setting a fake
content-type: the bytes decide, and the stored object's extension + content-type
are derived from the sniff, never from the upload.

:func:`looks_scriptable` is a defence-in-depth reject for SVG/HTML/XML/script
markup (an XSS vector if ever served inline) — redundant with the sniff today
(such files never match a raster magic number) but explicit so the intent is
clear and the guard survives any future widening of the allowed set.

Pure functions only (no Django, no I/O) so they are cheap to unit-test.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImageKind:
    """A permitted raster image family: its canonical content-type + extension."""

    content_type: str
    extension: str


_PNG = ImageKind("image/png", "png")
_JPEG = ImageKind("image/jpeg", "jpg")
_WEBP = ImageKind("image/webp", "webp")
_GIF = ImageKind("image/gif", "gif")

# The content-type whitelist the declared multipart type must fall in (coarse first
# gate; the magic-byte sniff is the real check). SVG (image/svg+xml) is deliberately
# absent — it is active markup, not a raster image (XSS).
ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
    kind.content_type for kind in (_PNG, _JPEG, _WEBP, _GIF)
)

# Leading markers of scriptable/active content — reject outright (XSS defence).
_SCRIPTY_MARKERS: tuple[bytes, ...] = (
    b"<?xml",
    b"<svg",
    b"<html",
    b"<!doctype",
    b"<script",
    b"<!--",
)


def sniff_image_kind(head: bytes) -> ImageKind | None:
    """Return the raster image family ``head`` actually is by magic number, else None.

    Only the leading signature is inspected — enough to distinguish the four allowed
    families and to reject anything else (text, SVG/HTML, arbitrary binary). The
    caller trusts this result over the client-declared content-type.
    """
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return _PNG
    if head.startswith(b"\xff\xd8\xff"):
        return _JPEG
    # RIFF container tagged WEBP: "RIFF" <4-byte size> "WEBP".
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return _WEBP
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return _GIF
    return None


def looks_scriptable(head: bytes) -> bool:
    """Return True if ``head`` opens with SVG/HTML/XML/script markup (reject → XSS).

    Case-insensitive and whitespace-tolerant on the leading bytes so ``  <SVG …``
    and ``<!DOCTYPE html>`` are both caught.
    """
    lowered = head.lstrip()[:64].lower()
    return any(marker in lowered for marker in _SCRIPTY_MARKERS)
