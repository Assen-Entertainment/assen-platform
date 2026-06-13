"""Base Django settings shared by every environment (CONSTRAINTS #14).

Environment-specific modules (dev, test) import everything from here and then
override. All external configuration is read through django-environ so secrets
never live in source; only `.env.example` is committed (CONSTRAINTS #27).
"""

from __future__ import annotations

from pathlib import Path

import environ

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
    "apps.safety",
    "apps.pos_lite",
    "apps.notification",
    "apps.feature_flag",
    "apps.admin_rbac",
    "apps.audit",
    "apps.event_log",
    "apps.dashboard",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

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

# Celery + Redis (ADR-0001). Broker/result backend come from env; beat schedule
# is a placeholder until periodic tasks are defined in later phases.
CELERY_BROKER_URL: str = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND: str = env(
    "CELERY_RESULT_BACKEND",
    default="redis://localhost:6379/1",
)
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE: dict[str, object] = {}
