"""Base Django settings shared by every environment (CONSTRAINTS #14).

Environment-specific modules (dev, test) import everything from here and then
override. All external configuration is read through django-environ so secrets
never live in source; only `.env.example` is committed (CONSTRAINTS #27).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import environ
from celery.schedules import crontab

# config/settings/base.py -> server/ is three parents up.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
)

# Read a local .env if present; CI and prod inject real environment variables.
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY: str = env("DJANGO_SECRET_KEY", default="insecure-dev-key-override-me")
DEBUG: bool = env("DJANGO_DEBUG")
ALLOWED_HOSTS: list[str] = env("DJANGO_ALLOWED_HOSTS")

# Fan signup OTP provider gate (ASS-98, Fan_Signup_Privacy_Policy §1/§8). The
# deterministic mock sender is dev/test only — anyone could reproduce its codes.
# Hardcoded False here (NOT env-driven) so a stray production env var cannot
# enable the mock; only the dev/test settings modules opt in. With no real SMS
# adapter wired yet, production stays False and the signup surface fails closed
# (503) rather than trust an unverifiable OTP — a real adapter replaces the mock
# behind a later infra/PII gate.
ENABLE_MOCK_FAN_OTP: bool = False

# Gated feature flags for the R3 round (KYC / 19+ / payment methods). Each mirrors
# the ENABLE_MOCK_FAN_OTP contract: hardcoded False here (NOT env-driven) so no
# stray production env var can flip them on; only the dev/test settings modules
# opt in. Every real integration behind them is a mock/skeleton — the real
# provider/PG/adult-content activation is a separate 대표·법무 gate (R3 계획
# 법무 경계 정본). Fail-closed: with the flag off the surface refuses (503) or
# hides gated data rather than trust an unverifiable path.
#
# - ENABLE_MOCK_KYC: the deterministic mock identity verifier (config.identity_verify).
#   Off → /fan/verify/* fails closed (503); no real NICE/PASS/KCB/아이핀 provider is
#   ever wired, and no 주민번호/CI/DI/생년월일 원본 is stored (only a derived
#   adult_verified flag + kyc_status).
# - ENABLE_ADULT_CONTENT: gates 19+ read exposure. Off → adult_only posts/products
#   are hidden from EVERYONE (§55: live activation = 법무 사인). On (dev/test) they
#   are shown only to an adult_verified viewer.
# - ENABLE_MOCK_PAYMENT: the deterministic mock payment tokenizer (config.payment).
#   Off → payment-method registration fails closed (503); no real PG tokenization,
#   and no card PAN/expiry/cvc is ever received-and-stored (only brand + last4 +
#   a mock token).
ENABLE_MOCK_KYC: bool = False
ENABLE_ADULT_CONTENT: bool = False
ENABLE_MOCK_PAYMENT: bool = False

# Per-user rate limiting on the fan write endpoints (follow/like/comment/post,
# SDLC 09 §4, E11/B4). On by default so dev/prod throttle real traffic; the test
# suite turns it off (config/settings/test.py) to stay deterministic across the
# many writes it fires for one fixture account. Env-overridable (default True, so
# prod stays throttled) for rapid smoke/load runs that fire many writes at once.
# See config.throttle.
FAN_WRITE_THROTTLE_ENABLED: bool = env.bool("FAN_WRITE_THROTTLE_ENABLED", default=True)

# Rate-limiter backend for the cross-cutting middleware limiter (config.ratelimit).
# "memory" (default) is the per-process in-memory limiter; "redis" selects the
# shared cross-worker limiter once it is wired (deployment-bound). An unwired value
# fails safe to in-memory rather than crash the request path — see get_rate_limiter.
RATELIMIT_BACKEND: str = env("RATELIMIT_BACKEND", default="memory")

# Number of trusted reverse-proxy hops in front of the app, for client-IP
# extraction in the rate limiters (config.clientip). Default 0 keeps REMOTE_ADDR
# (dev/no-proxy). Behind an ALB set TRUSTED_PROXY_HOPS=1 so the limiter keys on the
# real client from X-Forwarded-For instead of bucketing all traffic under the ALB.
TRUSTED_PROXY_HOPS: int = env.int("TRUSTED_PROXY_HOPS", default=0)

# Django contrib + third-party apps.
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "django_linear_migrations",
]

# 17 domain apps (CONSTRAINTS #38 — narrow app boundaries). Models land in
# P4/P5; these are empty skeletons for P0.
LOCAL_APPS = [
    "apps.identity",
    "apps.consent",
    "apps.fan",
    "apps.cast",
    "apps.schedule",
    "apps.reservation",
    "apps.visit",
    "apps.cheki",
    "apps.coupon",
    "apps.event_campaign",
    "apps.visit_guide",
    "apps.safety",
    "apps.pos_lite",
    "apps.notification",
    "apps.feature_flag",
    "apps.admin_rbac",
    "apps.audit",
    "apps.event_log",
    "apps.dashboard",
    # New-direction (creator platform) bounded contexts (SDLC 09 §3, E11/B1).
    # Migration-less like the rest — tables are built by `migrate --run-syncdb`.
    "apps.creator",
    "apps.social",
    "apps.content",
    "apps.commerce",
    "apps.membership",
    # Saved payment methods (R3): brand + last4 + mock PG token only — never a card
    # PAN/expiry/cvc. Migration-less like the rest (`migrate --run-syncdb`).
    "apps.payments",
]

# daphne must precede django.contrib.staticfiles so Channels' ASGI runserver
# override wins; channels provides the routing/consumer layer (ASS-240). Both are
# migration-less (no models).
INSTALLED_APPS = ["daphne", *DJANGO_APPS, "channels", *THIRD_PARTY_APPS, *LOCAL_APPS]

# Ordering follows Technical Architecture §3.5 #1. Only the outer cross-cutting
# concerns are Django middleware: request_id -> security headers -> rate limit.
# The next concerns in that pipeline — auth/session, consent gate, RBAC — are
# enforced at the Ninja layer (custom HttpBearer auth classes + the consent gate
# decorator), because they need the resolved route and authenticated account, not
# just the raw request. Idempotency sits further in, at the command layer (§3.5
# #3). The in-memory rate limiter is a skeleton; the production limiter shares
# state in Redis and is deployment-bound, so only the position is fixed here.
MIDDLEWARE = [
    "config.middleware.RequestIDMiddleware",
    # CORS must sit above anything that can emit a response (CommonMiddleware
    # etc.) so preflight OPTIONS short-circuits with the right headers. The
    # browser-facing web app calls the API cross-origin (NEXT_PUBLIC_API_URL),
    # so allowed origins are env-driven and CLOSED by default (SDLC 11 §4).
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "config.middleware.SecurityHeadersMiddleware",
    "config.middleware.InMemoryRateLimitMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Channels realtime (ASS-240). Realtime is a courtesy rail — it must never be a
# single point of failure — so the layer selection fails safe exactly like the
# rate limiter (config.ratelimit.get_rate_limiter): the single-process
# InMemoryChannelLayer by default (dev/test/one worker, no broker), and the shared
# cross-worker channels-redis layer ONLY when CHANNEL_LAYERS_BACKEND=redis AND
# channels-redis is installed AND CHANNEL_LAYERS_REDIS_URL is set. Anything short
# of that falls back to in-memory rather than crash boot. channels-redis is an
# optional extra (pyproject [project.optional-dependencies] realtime-redis) and is
# never installed in dev/test. Migration-less: channels/daphne ship no models.
CHANNEL_LAYERS_BACKEND: str = env("CHANNEL_LAYERS_BACKEND", default="memory")


def _build_channel_layers() -> dict[str, Any]:
    """Return the ``CHANNEL_LAYERS`` mapping, failing safe to the in-memory layer."""
    in_memory: dict[str, Any] = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }
    if CHANNEL_LAYERS_BACKEND.lower() != "redis":
        return in_memory
    redis_url = env("CHANNEL_LAYERS_REDIS_URL", default="")
    if not redis_url:
        return in_memory
    try:
        import channels_redis  # noqa: F401
    except ImportError:
        return in_memory
    return {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [redis_url]},
        },
    }


CHANNEL_LAYERS: dict[str, Any] = _build_channel_layers()

# PostgreSQL in dev/prod (CONSTRAINTS #14). The test environment overrides this
# with sqlite so the suite runs without a database server.
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://assen:assen@localhost:5432/assen",
    ),
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS — fail-closed: no origin is allowed unless the environment says so.
# dev.py opts in localhost web origins; prod supplies the real web origin(s).
CORS_ALLOWED_ORIGINS: list[str] = env.list("CORS_ALLOWED_ORIGINS", default=[])

# Celery + Redis (ADR-0001). Broker/result backend come from env; beat schedule
# is a placeholder until periodic tasks are defined in later phases.
CELERY_BROKER_URL: str = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND: str = env(
    "CELERY_RESULT_BACKEND",
    default="redis://localhost:6379/1",
)
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE: dict[str, object] = {
    # Reap unredeemed, long-expired QR check-in tokens hourly (ASS-151).
    "purge-expired-checkin-tokens": {
        "task": "apps.visit.tasks.purge_expired_checkin_tokens",
        "schedule": crontab(minute=0),
    },
}

# Structured logging (R4-W2, ASS-242). One dictConfig shared by every
# environment; the only axis that varies is the console formatter — dev/test keep
# the human-readable line, prod switches to the JSON formatter (see prod.py). Every
# record is stamped with the per-request correlation id via the request_id filter
# (config.observability.RequestIDLogFilter), so a log line traces back to the
# request that produced it. Handlers write to stdout only — the container runtime
# (CloudWatch) collects it; no file/socket sinks that could smuggle PII off-box.
LOG_LEVEL: str = env("DJANGO_LOG_LEVEL", default="INFO")


def build_logging(*, json_format: bool) -> dict[str, Any]:
    """Return the dictConfig ``LOGGING`` mapping.

    ``json_format`` selects the structured JSON formatter (prod) over the
    human-readable console formatter (dev/test). Both attach the request_id filter
    so the correlation id is available to whichever formatter renders the record.
    """
    formatter = "json" if json_format else "console"
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {"()": "config.observability.RequestIDLogFilter"},
        },
        "formatters": {
            "console": {
                "format": "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s",
            },
            "json": {"()": "config.observability.JsonLogFormatter"},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": formatter,
                "filters": ["request_id"],
            },
        },
        "root": {"handlers": ["console"], "level": LOG_LEVEL},
        "loggers": {
            # Standard hierarchy: framework noise and our own app tree both flow
            # through the single console handler. propagate=False so a record is
            # emitted once (by the logger's own handler), not re-emitted at root.
            "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
            "apps": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        },
    }


# dev/test inherit this human-readable config; prod overrides with json_format=True.
LOGGING: dict[str, Any] = build_logging(json_format=False)
