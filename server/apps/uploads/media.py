"""Gated media route — the read path for EVERY storage backend (대표 approved 07-18).

``config.urls`` mounts this at ``MEDIA_URL`` unconditionally: media is proxied through
Django on the local filesystem *and* on S3, rather than handed out bucket-direct via a
signed URL. That decision buys two things a signed-URL read cannot:

- **stable URLs.** A signed URL expires (~1h). ``Upload.url`` is persisted and copied
  verbatim into Post/Product ``media_url``, so minting reads from the backend meant
  every stored image broke an hour after upload. The served URL is now a pure function
  of the storage key (``apps.uploads.services.media_url_for_key``) and never goes
  stale.
- **takedown that actually takes effect.** A bucket-direct read never reaches Django,
  so no ``status`` check could run and an actioned image kept resolving for every
  outstanding signature. Every read now passes the check below, immediately, with no
  edge cache to purge.

The cost is bandwidth through the app tier, which is acceptable at soft-launch scale
and is what a CDN would later front (see the module docstring of
apps.uploads.services for what that would then oblige).

404 — not 403 — is deliberate: the takedown decision (and therefore the existence of a
report about this object) is operator-internal, and a distinguishable 403 would leak it
to anyone probing the URL. From the outside a taken-down image is simply gone, which is
also what a browser cache should treat it as.
"""

from __future__ import annotations

from collections.abc import Iterator

from django.core.files.storage import default_storage
from django.http import Http404, HttpRequest, StreamingHttpResponse
from django.http.response import HttpResponseBase

from apps.uploads.services import is_taken_down_media_path, upload_for_media_key

# Read size for the streamed response. Media is streamed, never slurped: an object is
# bounded by UPLOAD_MAX_BYTES (10 MiB default) but the app tier serves many at once, so
# buffering whole files would make concurrent reads a memory ceiling.
_CHUNK_BYTES = 64 * 1024

# Content-Type for an object we hold no Upload row for (fixtures, seeded demo media).
# The row is the authority on what a stored object is — its type came from the upload's
# magic-byte sniff — so an object with no row is one nothing vouches for, and it gets
# the inert type rather than a guess. With nosniff that is a download, never active
# content. Never sniffed from the bytes at read time: that would re-open exactly the
# hole the write-time sniff closes.
_UNVOUCHED_CONTENT_TYPE = "application/octet-stream"


def _is_safe_key(key: str) -> bool:
    """Whether ``key`` is a plain relative storage key and not a traversal attempt.

    Replaces the normalisation ``django.views.static.serve`` used to do for us: the URL
    pattern captures the key verbatim, so ``../`` must be refused here. The local
    backend's ``safe_join`` would refuse it anyway (as a 400 + an exception), and S3
    has no traversal to attempt — this makes it a quiet 404 on both, which is what a
    probe deserves.
    """
    if not key or key.startswith("/") or "\\" in key or "\x00" in key:
        return False
    return ".." not in key.split("/")


def _stream(key: str) -> Iterator[bytes]:
    """Yield the object's bytes in bounded chunks, closing the handle when done.

    Lazy on purpose (Windows). The handle is opened on the first chunk pulled — not
    when the response is constructed — so a caller that only inspects status/headers
    never holds the file open, and a takedown moving that object cannot be blocked by
    it. Whoever consumes the iterator closes it: a WSGI/ASGI server does so after the
    body, and ``HttpResponseBase.close()`` closes the generator directly (it is
    registered as a resource closer), which fires the ``with`` here. Correctness never
    depends on the caller remembering to.
    """
    with default_storage.open(key, "rb") as handle:
        while True:
            chunk = handle.read(_CHUNK_BYTES)
            if not chunk:
                break
            yield chunk


def serve_upload(request: HttpRequest, path: str) -> HttpResponseBase:
    """Stream a stored media object unless it is taken down, quarantined, or gone (404).

    Reads through ``default_storage``, so one code path covers the local filesystem and
    S3 — the same reason the write site knows no backend (apps.uploads.api).
    """
    del request  # the object is addressed entirely by its key
    if not _is_safe_key(path) or is_taken_down_media_path(path):
        raise Http404("media object is not available")
    # Ask the store before promising a body: a key with no object must be a 404, not a
    # 500 raised half-way through a 200 response that already claimed to have one.
    if not default_storage.exists(path):
        raise Http404("media object is not available")

    upload = upload_for_media_key(path)
    response = StreamingHttpResponse(
        _stream(path),
        content_type=upload.content_type if upload else _UNVOUCHED_CONTENT_TYPE,
    )
    # Belt-and-braces with SecurityHeadersMiddleware's global nosniff: this route hands
    # out user-supplied bytes, so the guarantee that the browser honours our declared
    # type is stated where those bytes are served rather than inherited from middleware
    # ordering somewhere else.
    response["X-Content-Type-Options"] = "nosniff"
    # inline (never attachment): these are feed images and must render. Safety comes
    # from the row-pinned image/* type + nosniff, not from forcing a download. Mirrors
    # what the S3 write path stamps on the object (config.settings.base).
    response["Content-Disposition"] = "inline"
    # private: media is gated (a takedown must stop it for everyone at once), so no
    # shared proxy may hold a copy that outlives the decision. Same value the stored
    # objects carry, so the posture does not change with the backend.
    response["Cache-Control"] = "private, max-age=300"
    return response
