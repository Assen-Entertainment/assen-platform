"""Production settings: fail-closed on required env, security headers on.

Deployment target = ECS Fargate behind an ALB (docs/adr/0003-hosting-aws.md).
Unlike dev/test, every security-relevant value must come from the environment —
there are NO insecure defaults here: a missing DJANGO_SECRET_KEY or
DJANGO_ALLOWED_HOSTS raises at boot instead of silently shipping the dev key
(base.py's default exists only for local convenience).
"""

from __future__ import annotations

import environ
from django.core.exceptions import ImproperlyConfigured

from config.observability import init_sentry
from config.settings.base import *  # noqa: F403
from config.settings.base import build_logging, env

DEBUG = False

# Required — read through a FRESH Env: base.py's shared `env` carries schema
# defaults (e.g. DJANGO_ALLOWED_HOSTS → ["localhost", ...]) that would silently
# satisfy a "required" read here. A schema-less Env raises ImproperlyConfigured
# when the variable is absent, which is the fail-closed behaviour we want.
_required = environ.Env()
SECRET_KEY = _required("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = _required.list("DJANGO_ALLOWED_HOSTS")

# Data & task-broker stores are as security-critical as the secret key. base.py
# ships dev-convenience defaults (postgres://assen:assen@localhost, redis://
# localhost) so a mis-provisioned prod would NOT fail at boot — it would quietly
# point at a non-existent local store and fail only at first query. Re-read them
# through the schema-less Env so their ABSENCE fails closed at boot, exactly like
# SECRET_KEY/ALLOWED_HOSTS above (ASS-265). Celery's broker/result backends are
# genuinely used (the beat/worker services); the in-memory rate-limiter and
# channels layer fail *safe* to in-process, so no generic REDIS_URL is required
# here until those Redis backends are actually wired (ASS-268).
DATABASES = {"default": _required.db("DATABASE_URL")}
CELERY_BROKER_URL = _required("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = _required("CELERY_RESULT_BACKEND")

# Phone-identifier HMAC key (ASS-287 A-2): a dedicated secret keying
# Account.auth_subject_hash, separate from SECRET_KEY. Required and >= 32 bytes so
# a missing/weak key fails closed at boot rather than silently weakening the hash.
PHONE_IDENTIFIER_HMAC_KEY = _required("PHONE_IDENTIFIER_HMAC_KEY")
if len(PHONE_IDENTIFIER_HMAC_KEY.encode("utf-8")) < 32:
    raise ImproperlyConfigured("PHONE_IDENTIFIER_HMAC_KEY must be at least 32 bytes.")

# Rate limiting must be shared + correctly proxy-aware in production (ASS-295). The
# per-process in-memory limiter cannot bound a multi-worker fleet (each worker keeps
# its own quota → N× the intended limit), and a wrong proxy-hop count either trusts
# a spoofable client IP or buckets every user onto the load-balancer IP. Require the
# shared Redis backend, its URL, and an explicit proxy-hop count (>=1 behind the ALB
# that terminates TLS above). Re-read via env so the check is mypy-clean and mirrors
# how base.py computed the values.
if env("RATELIMIT_BACKEND", default="memory") != "redis":
    raise ImproperlyConfigured(
        "RATELIMIT_BACKEND must be 'redis' in production — the in-memory limiter "
        "does not bound a multi-worker fleet (ASS-295)."
    )
if not env("RATELIMIT_REDIS_URL", default=""):
    raise ImproperlyConfigured(
        "RATELIMIT_REDIS_URL must be set in production (ASS-295)."
    )
if env.int("TRUSTED_PROXY_HOPS", default=0) < 1:
    raise ImproperlyConfigured(
        "TRUSTED_PROXY_HOPS must be >= 1 behind the load balancer, else every user "
        "buckets onto the proxy IP (ASS-295)."
    )

# TLS terminates at the ALB; trust its forwarded proto header so Django knows
# the original request was HTTPS (required for secure-cookie/redirect logic).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
# ALB target health checks probe /healthz and /readyz over plain HTTP without
# X-Forwarded-Proto — a blanket redirect would 301 the probe and keep every
# task "unhealthy" forever. Exempt exactly those paths (SDLC 11 §6).
SECURE_REDIRECT_EXEMPT = [r"^healthz$", r"^readyz$"]

# HSTS (ASS-278) — a full year by default now that the domain/TLS setup is stable;
# still env-tunable so ops can dial it down (e.g. while rotating certs/domains)
# without a code change. SECURE_HSTS_PRELOAD stays opt-in (default False): submitting
# to the browser preload list is very hard to reverse (removal takes months and
# affects every subdomain), so it must be a deliberate ops decision, not a default.
SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = env.bool("DJANGO_HSTS_PRELOAD", default=False)

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Web origin(s) allowed to POST with CSRF (e.g. https://assen.example).
CSRF_TRUSTED_ORIGINS: list[str] = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# Browser-facing web origin(s) for CORS (e.g. https://assen.example). Empty by
# default (closed): if the deployment routes web+api same-origin behind one
# ALB/CDN (SDLC 11 §4 option B), leave this unset.
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

# Structured JSON logging to stdout; the container runtime (CloudWatch) collects
# it. Same dictConfig as base, with the JSON formatter selected — each line is a
# machine-parseable object carrying the request-id correlation field.
LOGGING = build_logging(json_format=True)

# Error tracking. No-op unless SENTRY_DSN is set (config.observability.init_sentry),
# so an unconfigured deploy stays silent; when wired it reports with PII scrubbed
# and send_default_pii=False. Called at settings import — Sentry's Django
# integration hooks lazily, so the app registry need not be ready yet.
init_sentry()
