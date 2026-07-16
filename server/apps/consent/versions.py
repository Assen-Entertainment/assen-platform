"""Server-issued consent-document version registry (the presented-policy source).

Consent capture must record WHICH policy text a fan agreed to, not merely that they
agreed — otherwise there is no proof of the exact terms/privacy/age wording behind a
grant. This module is the single source of truth for the *current* version string of
each versioned consent document, so signup can stamp the presented version onto every
:class:`~apps.consent.models.ConsentRecord`, and the (anonymous) web signup page can
fetch + echo the same versions it displayed.

⚠️ 법무-게이트: the version VALUES below are PLACEHOLDERS. Legal has not finalised or
versioned the actual document copy yet (architecture: consent module — 최종 문구는
승인 필요). This is the *plumbing*: when legal publishes a new document revision that
requires re-consent, bump the string here — the consent gate keys on (kind, version),
so a bumped version forces the fan to re-agree. Only this registry changes; no code
change and no migration is needed (``ConsentRecord.version`` already stores the value).
"""

from __future__ import annotations

from apps.consent.models import ConsentKind

# Current presented version per consent document, keyed by ``ConsentKind`` value.
# Placeholder values pending 법무 sign-off (see module docstring). ``age`` is the
# age-confirmation document presented at signup (만 14세 이상 self-declaration); the
# 성인(19+) 인증 ``ConsentKind.AGE`` record is written by the separate KYC flow, which
# carries its own version string today.
CONSENT_DOC_VERSIONS: dict[str, str] = {
    ConsentKind.TERMS.value: "2026-07-16.draft",
    ConsentKind.PRIVACY.value: "2026-07-16.draft",
    ConsentKind.AGE.value: "2026-07-16.draft",
}


def consent_doc_version(kind: str) -> str:
    """Return the current presented version for a consent ``kind``.

    KeyError-safe: an unversioned/unknown kind (e.g. ``rule``/``marketing``, which
    carry their own dynamic per-grant version strings) returns ``""`` so the result
    can be passed straight into :func:`~apps.consent.services.record_consent` (whose
    ``version`` is a plain string) without a guard at the call site.
    """
    return CONSENT_DOC_VERSIONS.get(kind, "")
