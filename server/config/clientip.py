"""Trusted-proxy-aware client IP extraction (R5-W1A — ALB rate-limit keying).

Behind a load balancer (ALB) the app's ``REMOTE_ADDR`` is the balancer, not the
caller — so every request shares one rate-limit bucket. The fix is to read the
client from the ``X-Forwarded-For`` chain, but XFF is client-writable: only the
right-hand entries appended by *our* trusted infrastructure can be believed. This
module extracts the client address ``TRUSTED_PROXY_HOPS`` positions from the right
of the chain (the address the first trusted proxy saw), clamped so a client-forged
prefix can never be selected.

``TRUSTED_PROXY_HOPS`` defaults to 0, which keeps ``REMOTE_ADDR`` (dev/no-proxy
behaviour is unchanged). Set it to the number of trusted proxies in front of the
app (e.g. 1 for a single ALB) in the deployment environment.
"""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest


def _trusted_hops() -> int:
    """Number of trusted proxy hops from ``settings`` (default 0), never negative."""
    try:
        hops = int(getattr(settings, "TRUSTED_PROXY_HOPS", 0))
    except (TypeError, ValueError):
        return 0
    return max(0, hops)


def client_ip(request: HttpRequest, trusted_proxies: int | None = None) -> str:
    """Return the client IP for rate-limit keying, defending against XFF spoofing.

    With ``trusted_proxies`` (default ``TRUSTED_PROXY_HOPS``) at 0, returns
    ``REMOTE_ADDR`` unchanged — the direct-peer address, correct when no trusted
    proxy sits in front. Otherwise the client is the entry ``trusted_proxies``
    positions from the right of ``X-Forwarded-For`` (the address the first trusted
    proxy observed), clamped to the leftmost entry so a shorter-than-declared chain
    — or a client-forged prefix — can never push the selection past the trusted
    tail. Falls back to ``REMOTE_ADDR`` when XFF is absent or empty.
    """
    hops = _trusted_hops() if trusted_proxies is None else max(0, trusted_proxies)
    remote_addr = str(request.META.get("REMOTE_ADDR", "unknown"))
    if hops == 0:
        return remote_addr
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if not forwarded:
        return remote_addr
    addrs = [part.strip() for part in str(forwarded).split(",") if part.strip()]
    if not addrs:
        return remote_addr
    return addrs[-min(hops, len(addrs))]
