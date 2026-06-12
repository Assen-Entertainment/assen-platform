"""Object-storage signed-URL adapter interface and a local mock.

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
