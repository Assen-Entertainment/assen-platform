"""Consent gate: block business commands for accounts lacking required consent.

Per the middleware ordering (Technical Architecture §3.5), the consent gate sits
at the Ninja/command layer — *not* as Django middleware — right after auth and
before RBAC and the business command. This module provides both a direct check
(``has_consent`` / ``assert_consent``) for command-layer code and a decorator
(``require_consent``) for endpoint handlers, so a command cannot run for a fan
who has not granted the consent it requires.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from functools import wraps
from typing import Any, TypeVar

from apps.consent.models import ConsentRecord
from apps.identity.models import Account

F = TypeVar("F", bound=Callable[..., Any])


class ConsentRequired(Exception):
    """Raised when an account attempts a command without the required consent.

    A distinct exception lets the API layer translate it to a specific 403 with a
    "consent needed" code instead of a generic error.
    """

    def __init__(self, kind: str, version: str | None = None) -> None:
        """Capture which consent kind/version was missing for the response."""
        self.kind = kind
        self.version = version
        detail = f"Consent '{kind}'" + (f" v{version}" if version else "")
        super().__init__(f"{detail} is required before this action.")


def has_consent(account: Account, *, kind: str, version: str | None = None) -> bool:
    """Return whether ``account`` has granted ``kind`` (optionally at ``version``).

    When ``version`` is given, only a grant at that exact version satisfies the
    check — this is how re-consent after a wording change is enforced.
    """
    qs = ConsentRecord.objects.filter(account=account, kind=kind)
    if version is not None:
        qs = qs.filter(version=version)
    return qs.exists()


def assert_consent(account: Account, *, kind: str, version: str | None = None) -> None:
    """Raise :class:`ConsentRequired` if the consent is missing.

    The imperative form used by command-layer code that is not an endpoint
    handler (e.g. service functions invoked by jobs).
    """
    if not has_consent(account, kind=kind, version=version):
        raise ConsentRequired(kind, version)


def require_consent(
    *, kind: str, version: str | None = None
) -> Callable[[F], F]:
    """Decorate a Ninja handler so it runs only if the caller has consented.

    Resolves the account from ``request.account`` (set by the opaque-token auth
    class) or ``request.auth``. Raising before the wrapped body runs guarantees
    the business command never executes without consent.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(request: Any, *args: Any, **kwargs: Any) -> Any:
            account = getattr(request, "account", None) or getattr(
                request, "auth", None
            )
            if not isinstance(account, Account):
                raise ConsentRequired(kind, version)
            assert_consent(account, kind=kind, version=version)
            return func(request, *args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def missing_consents(
    account: Account, *, required: Iterable[tuple[str, str]]
) -> list[tuple[str, str]]:
    """Return the (kind, version) pairs from ``required`` the account lacks.

    Lets a signup/onboarding flow report everything outstanding at once rather
    than failing one consent at a time.
    """
    return [
        (kind, version)
        for kind, version in required
        if not has_consent(account, kind=kind, version=version)
    ]
