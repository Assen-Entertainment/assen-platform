"""Media-storage readiness predicate, signed-URL adapter interface, and a local mock.

:func:`media_storage_ready` answers "can ``default_storage`` actually hold an object?"
— half of the upload-accept gate (apps.uploads.api).

P0 ships the boundary and a self-contained local mock; the real S3/GCS signer
lands later. Cheki images and safety attachments (P5) need time-limited access
URLs, and the safety-detail separation principle means those objects must not be
world-readable. Defining :class:`SignedUrlAdapter` now lets that future code
depend on an interface, while the mock issues HMAC-signed, expiring tokens so the
issue/verify/expiry behaviour can be tested without a cloud account.

Lives in ``config/`` (infrastructure), not a domain app: it is cross-cutting and
carries no model, mirroring the other ``config/`` infra modules (api, celery).
"""

from __future__ import annotations

import hashlib
import hmac
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlparse

from django.conf import settings

# Storage BACKEND paths that hand bytes to a real object store (as opposed to the
# local filesystem). These are the only backends that can be configured into a state
# that looks correct but can store nothing (a bucket-less S3), which is the sole thing
# :func:`media_storage_ready` can decide from settings alone. Kept as a set of dotted
# paths rather than an isinstance check so the predicate stays cheap and importable
# without django-storages installed (dev/test do not install it).
_OBJECT_STORAGE_BACKENDS: frozenset[str] = frozenset(
    {
        "storages.backends.s3.S3Storage",
        "storages.backends.s3boto3.S3Boto3Storage",
    }
)


def media_storage_ready() -> bool:
    """Whether ``default_storage`` is pointed somewhere an upload can be stored.

    Half of the upload gate (apps.uploads.api): uploads are accepted only when
    ALLOW_UPLOADS is on AND this says the backend is usable. The failure it exists to
    prevent is unchanged — never accept bytes that cannot come back — but the shape of
    that question changed: Django now serves every media byte itself, on every backend,
    through the gated view (apps.uploads.media). "Does a serving path exist" is
    therefore no longer a variable (it is always Django), and all that is left to
    establish is that the *store* has somewhere to put the object.

    Exactly one misconfiguration is decidable from settings: an object-storage backend
    naming no bucket. Its BACKEND reads as correct, so nothing else would catch it, yet
    every ``save()`` against it fails — this is the misconfiguration most likely to
    reach production, because an empty ``DJANGO_MEDIA_S3_BUCKET`` is silent.

    Any other backend (the local filesystem in dev/test/demo, a test double) is treated
    as usable. Whether the disk or the bucket is *actually* writable is a runtime fact
    no settings predicate can honestly answer, and pretending otherwise here would only
    move the failure, not detect it.
    """
    default = settings.STORAGES.get("default", {})
    if default.get("BACKEND", "") not in _OBJECT_STORAGE_BACKENDS:
        return True
    options = default.get("OPTIONS", {})
    if not isinstance(options, dict):
        return False
    return bool(options.get("bucket_name"))


@dataclass(frozen=True)
class SignedUrl:
    """A signed URL and the absolute epoch second it expires at."""

    url: str
    expires_at: int


class SignedUrlAdapter(ABC):
    """Boundary for minting and verifying time-limited object access URLs."""

    @abstractmethod
    def generate(self, *, object_key: str, expires_in: int) -> SignedUrl:
        """Return a signed URL granting access to ``object_key`` for a window."""
        raise NotImplementedError

    @abstractmethod
    def verify(self, url: str) -> bool:
        """Return whether ``url`` is correctly signed and not yet expired."""
        raise NotImplementedError


class LocalMockSignedUrlAdapter(SignedUrlAdapter):
    """Local HMAC-based signer used in P0 and tests.

    Signs ``object_key`` + expiry with a secret so a tampered key or expiry fails
    verification, and treats ``now > expiry`` as expired. This reproduces the
    *contract* of a cloud signer (unguessable, bound to the object, time-limited)
    without any external dependency. Not for production: a real adapter delegates
    to the storage provider's signer.
    """

    def __init__(self, *, secret: str, base_url: str = "https://mock-store.local") -> None:
        """Bind the signer to a secret and a base URL for generated links."""
        self._secret = secret.encode("utf-8")
        self._base_url = base_url.rstrip("/")

    def _sign(self, object_key: str, expires_at: int) -> str:
        """Compute the HMAC-SHA256 signature over the key and expiry.

        Binding the signature to both fields prevents swapping the object or
        extending the lifetime of an already-issued URL.
        """
        msg = f"{object_key}:{expires_at}".encode()
        return hmac.new(self._secret, msg, hashlib.sha256).hexdigest()

    def generate(self, *, object_key: str, expires_in: int) -> SignedUrl:
        """Mint a signed URL valid for ``expires_in`` seconds from now."""
        if expires_in <= 0:
            raise ValueError("expires_in must be positive.")
        expires_at = int(time.time()) + expires_in
        signature = self._sign(object_key, expires_at)
        query = urlencode(
            {"key": object_key, "expires": expires_at, "sig": signature}
        )
        return SignedUrl(
            url=f"{self._base_url}/{object_key}?{query}", expires_at=expires_at
        )

    def verify(self, url: str) -> bool:
        """Return True only if the signature matches and the URL is unexpired.

        Uses a constant-time signature comparison and recomputes the expected
        signature from the URL's own fields, so neither tampering nor replay past
        expiry verifies.
        """
        params = parse_qs(urlparse(url).query)
        try:
            object_key = params["key"][0]
            expires_at = int(params["expires"][0])
            signature = params["sig"][0]
        except (KeyError, IndexError, ValueError):
            return False
        expected = self._sign(object_key, expires_at)
        if not hmac.compare_digest(expected, signature):
            return False
        return time.time() <= expires_at
