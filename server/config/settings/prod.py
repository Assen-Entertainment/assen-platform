"""Production settings: fail-closed on required env, security headers on.

Deployment target = ECS Fargate behind an ALB (docs/adr/0003-hosting-aws.md).
Unlike dev/test, every security-relevant value must come from the environment —
there are NO insecure defaults here: a missing DJANGO_SECRET_KEY or
DJANGO_ALLOWED_HOSTS raises at boot instead of silently shipping the dev key
(base.py's default exists only for local convenience).
"""

from __future__ import annotations

import environ

from config.settings.base import *  # noqa: F403
from config.settings.base import env

DEBUG = False

# Required — read through a FRESH Env: base.py's shared `env` carries schema
# defaults (e.g. DJANGO_ALLOWED_HOSTS → ["localhost", ...]) that would silently
# satisfy a "required" read here. A schema-less Env raises ImproperlyConfigured
# when the variable is absent, which is the fail-closed behaviour we want.
_required = environ.Env()
SECRET_KEY = _required("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = _required.list("DJANGO_ALLOWED_HOSTS")

# TLS terminates at the ALB; trust its forwarded proto header so Django knows
# the original request was HTTPS (required for secure-cookie/redirect logic).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
# ALB target health checks probe /healthz over plain HTTP without
# X-Forwarded-Proto — a blanket redirect would 301 the probe and keep every
# task "unhealthy" forever. Exempt exactly that path (SDLC 11 §6).
SECURE_REDIRECT_EXEMPT = [r"^healthz$"]

# HSTS — start modest; raise to a year once the domain set is stable.
SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=3600)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Web origin(s) allowed to POST with CSRF (e.g. https://assen.example).
CSRF_TRUSTED_ORIGINS: list[str] = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# Browser-facing web origin(s) for CORS (e.g. https://assen.example). Empty by
# default (closed): if the deployment routes web+api same-origin behind one
# ALB/CDN (SDLC 11 §4 option B), leave this unset.
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

# Structured-ish console logging; the container runtime (CloudWatch) collects stdout.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "console"},
    },
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", default="INFO")},
}
