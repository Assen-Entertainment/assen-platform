"""Magic-byte + Pillow decode image validation for uploaded media (the upload
security boundary).

The client-declared multipart ``Content-Type`` is trivially spoofable, so it is
only a coarse first gate (:data:`ALLOWED_CONTENT_TYPES`). The next check is
:func:`sniff_image_kind`, which inspects the file's leading bytes (magic
numbers) and returns the image family the bytes *actually are* — or ``None`` for
anything that is not one of the four allowed raster formats. That is what defeats
an attacker renaming ``payload.svg`` to ``avatar.png`` / setting a fake
content-type: the bytes decide, and the stored object's extension + content-type
are derived from the sniff, never from the upload.

:func:`verify_image_decodes` is the deeper check that runs on the *full* payload
(after the sniff, which only inspects the leading 64 bytes): it asks Pillow to
actually decode the file as ``kind`` via ``Image.open(...).verify()``, which
catches truncated/corrupted files and polyglots that carry a valid raster
signature but are not a structurally valid image past that. It also enforces a
dimension cap and a total-pixel-count cap (decompression-bomb guard) before any
pixel data is decoded.

:func:`looks_scriptable` is *secondary* defence-in-depth: the primary XSS control
is that the stored object's content-type is derived from the magic-byte sniff (never
the client) and every response carries ``X-Content-Type-Options: nosniff`` (set
globally by SecurityMiddleware / SecurityHeadersMiddleware), so the browser will not
re-interpret a stored raster as active markup — even a polyglot crafted to smuggle
script past the 64-byte sniff window. The scan is a redundant early reject for
SVG/HTML/XML/script markup (such files never match a raster magic number anyway) but
explicit so the intent is clear and the guard survives any future widening of the
allowed set.

Pure functions only (no Django, no I/O) — ``verify_image_decodes`` takes its bounds
as explicit arguments rather than reading Django settings, so this module stays
cheap to unit-test.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from PIL import Image


@dataclass(frozen=True)
class ImageKind:
    """A permitted raster image family: content-type, extension, Pillow format name."""

    content_type: str
    extension: str
    pillow_format: str


_PNG = ImageKind("image/png", "png", "PNG")
_JPEG = ImageKind("image/jpeg", "jpg", "JPEG")
_WEBP = ImageKind("image/webp", "webp", "WEBP")
_GIF = ImageKind("image/gif", "gif", "GIF")

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


def verify_image_decodes(
    data: bytes,
    kind: ImageKind,
    *,
    max_pixels: int,
    max_dimension: int,
) -> bool:
    """Return True iff Pillow can structurally decode ``data`` as ``kind`` within bounds.

    Runs on the full payload *after* :func:`sniff_image_kind` has already confirmed
    the leading magic bytes match ``kind``. This is the deeper check that catches
    truncated, corrupted, or polyglot payloads that pass the 64-byte header sniff
    but are not a real decodable image (e.g. a valid PNG signature followed by
    garbage instead of real chunks, or a body swapped for another file entirely).

    Two independent guards against decompression-bomb style huge images: the
    reported pixel dimensions must not exceed ``max_dimension`` on either axis, and
    the total pixel count (``width * height``) must not exceed ``max_pixels``. Both
    are checked from the header Pillow already parsed on ``Image.open`` — *before*
    ``verify()`` touches any pixel data. Pillow's own built-in guard
    (:class:`PIL.Image.DecompressionBombError` / ``DecompressionBombWarning``,
    keyed off ``Image.MAX_IMAGE_PIXELS``) is also treated as a rejection, as a
    second independent net.

    ``Image.open`` only parses the header (cheap, lazy); the actual decode/structure
    check happens in ``verify()``. The image object is unusable after ``verify()``
    per Pillow's contract, so size/format are read *before* calling it. The format
    Pillow detects is also cross-checked against ``kind`` (the sniff's own verdict)
    as a redundant consistency check.

    Any decode failure (unidentified format, truncated stream, bad checksums, …) is
    treated as rejection — this function never raises; a broad catch is intentional
    here because the caller only needs a yes/no answer for an untrusted payload.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as img:
                width, height = img.size
                if width > max_dimension or height > max_dimension:
                    return False
                if width * height > max_pixels:
                    return False
                if img.format != kind.pillow_format:
                    return False
                img.verify()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        return False
    except Exception:
        return False
    return True


# Info keys that some Pillow encoders re-embed from the *source* image's ``info``
# when the caller does not override them (empirically verified against Pillow 11.3):
# the PNG encoder re-writes ``icc_profile`` and the GIF encoder re-writes ``comment``
# on a plain re-save. The JPEG and WEBP encoders read metadata only from explicit
# save params, so a plain re-encode already drops their EXIF/XMP/ICC; EXIF text
# chunks are likewise not re-embedded by any of the four encoders. Deleting these
# keys before saving makes the re-encode drop ALL metadata for every allowed format.
_METADATA_INFO_KEYS: tuple[str, ...] = (
    "exif",
    "xmp",
    "icc_profile",
    "comment",
    "photoshop",
    "iptc",
)


def strip_metadata(data: bytes, kind: ImageKind) -> bytes:
    """Canonically re-encode ``data`` as ``kind``, returning bytes with no metadata.

    A structurally valid JPEG/PNG/WEBP can carry EXIF/XMP/GPS/ICC metadata (an
    embedded phone number, a GPS location, a serial number, …). :func:`verify_image_decodes`
    only *decode-verifies*; it does not strip that metadata, so the original bytes —
    PII and all — would otherwise be stored and served verbatim. This re-encodes the
    pixels through Pillow in the *same* sniffed format, which is the authoritative way
    to guarantee only image data (no ancillary metadata chunks) survives.

    Must run only *after* :func:`verify_image_decodes` has passed: at that point the
    image's dimensions and total pixel count are already capped, so the full decode
    this performs (re-encoding necessarily loads every pixel, unlike the lazy
    ``verify()``) cannot be a decompression bomb — it re-uses the same bounded bytes.

    Animated GIF/WEBP keep their frames (``save_all``); frame timing/loop and
    transparency live under structural ``info`` keys that are preserved — only the
    metadata keys in :data:`_METADATA_INFO_KEYS` are dropped. JPEG is re-saved with
    ``quality="keep"`` so re-encoding a photo does not add a generation of lossy
    recompression artifacts (the source is always a Pillow-decodable JPEG here).
    """
    with Image.open(BytesIO(data)) as img:
        animated = bool(getattr(img, "is_animated", False))
        # Drop the metadata keys the encoders would otherwise carry over from the
        # source; structural keys (duration/loop/disposal/transparency/…) are kept.
        for key in _METADATA_INFO_KEYS:
            img.info.pop(key, None)
        save_kwargs: dict[str, Any] = {}
        if animated:
            save_kwargs["save_all"] = True
        if kind.pillow_format == "JPEG":
            save_kwargs["quality"] = "keep"
        out = BytesIO()
        img.save(out, format=kind.pillow_format, **save_kwargs)
        return out.getvalue()


def looks_scriptable(head: bytes) -> bool:
    """Return True if ``head`` opens with SVG/HTML/XML/script markup (reject → XSS).

    Case-insensitive and whitespace-tolerant on the leading bytes so ``  <SVG …``
    and ``<!DOCTYPE html>`` are both caught.
    """
    lowered = head.lstrip()[:64].lower()
    return any(marker in lowered for marker in _SCRIPTY_MARKERS)
