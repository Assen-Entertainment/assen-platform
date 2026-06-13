"""Server-side Set-Cookie option helpers for web token delivery (ADR-0002).

HUMAN-REVIEW-REQUIRED: auth (CONSTRAINTS #26).

The server does not decide where the client stores tokens (web = httpOnly cookie,
app = secure platform storage) — that is a client concern. Its sole job is to
emit cookies with the correct hardening flags when the web flow asks for them.
This helper centralises those flags so every cookie the auth layer sets is
``httponly`` + ``secure`` + ``samesite`` consistently.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from django.http import HttpResponse

# SameSite policy values Django accepts on Set-Cookie.
SameSite = Literal["Lax", "Strict", "None"]

# Default cookie names for the web surface. The app surface does not use cookies.
ACCESS_COOKIE_NAME = "assen_access"
REFRESH_COOKIE_NAME = "assen_refresh"


def set_auth_cookie(
    response: HttpResponse,
    *,
    name: str,
    value: str,
    expires_at: datetime,
    secure: bool = True,
    samesite: SameSite = "Lax",
    path: str = "/",
) -> HttpResponse:
    """Attach a hardened auth cookie to ``response`` and return it.

    Flags are non-optional by intent: ``httponly`` blocks JS token theft (XSS
    defense, ADR-0002), ``secure`` keeps the cookie off plaintext transport, and
    ``samesite`` constrains cross-site send (CSRF defense). ``secure`` is a
    parameter only so local non-HTTPS development can relax it explicitly.
    """
    response.set_cookie(
        key=name,
        value=value,
        expires=expires_at,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path=path,
    )
    return response


def clear_auth_cookie(
    response: HttpResponse, *, name: str, path: str = "/"
) -> HttpResponse:
    """Delete an auth cookie (used on logout) and return the response."""
    response.delete_cookie(key=name, path=path)
    return response
