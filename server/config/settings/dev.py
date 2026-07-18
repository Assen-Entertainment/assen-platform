"""Development settings: DEBUG on, eager-friendly Celery, local hosts."""

from __future__ import annotations

import os

# Shared cross-worker channel layer (ASS-268 follow-up): dev/compose run daphne as
# the ASGI server, so the real channels-redis layer is exercised locally instead of
# base.py's single-process in-memory default. Dedicated DB (…/3), distinct from the
# rate limiter (…/2) and Celery's broker/result backend (…/0, …/1) on the same Redis
# instance. These must land in os.environ *before* the base import below, because
# base.py._build_channel_layers() reads CHANNEL_LAYERS_BACKEND/CHANNEL_LAYERS_REDIS_URL
# via env() at base.py's own import time — setting plain module attributes here would
# be too late to affect it. setdefault() lets a real env (e.g. docker-compose) still
# win. base.py still fails safe to in-memory if channels-redis isn't importable.
os.environ.setdefault("CHANNEL_LAYERS_BACKEND", "redis")
os.environ.setdefault("CHANNEL_LAYERS_REDIS_URL", "redis://localhost:6379/3")

from config.settings.base import *  # noqa: E402, F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Accept uploads locally (base.py fails this closed for unconfigured environments).
# Nothing else is needed: dev has no S3 backend, so default_storage is the local
# filesystem — usable by definition — and Django serves it back (config.urls), exactly
# as it does in production.
ALLOW_UPLOADS = True

# Fan signup uses the deterministic mock OTP locally (no SMS provider wired).
ENABLE_MOCK_FAN_OTP = True
ENABLE_MOCK_SOCIAL_AUTH = True
# Email + password auth uses the mock (log-only) email sender locally, and echoes the
# verification token in the signup response so the confirm flow is completable without
# a real inbox (no SMTP wired; see base.py).
ENABLE_MOCK_EMAIL = True
EMAIL_VERIFY_RETURN_TOKEN = True

# R3 gated features opt in locally: the mock KYC verifier + mock payment tokenizer
# are wired, and 19+ read exposure is on so the age-gate/blur flows can be exercised
# against seeded adult items. All three are mock/skeleton — no real provider, PG, or
# real adult content is involved (production keeps these False; see base.py).
ENABLE_MOCK_KYC = True
ENABLE_ADULT_CONTENT = True
ENABLE_MOCK_PAYMENT = True
# Mock push transport locally so the operator dispatch surface returns success
# instead of the prod fail-closed 503 (no real FCM/APNs wired; see base.py).
ENABLE_MOCK_PUSH = True

# Local web dev server origins (Next.js) — override via env when ports differ.
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:3000", "http://127.0.0.1:3000"],
)

# Web cookie auth (ADR-0002, ASS-237): the SPA carries the httpOnly session cookie
# and echoes the CSRF token on unsafe methods. The same-origin Next.js rewrites
# proxy is the default in dev (browser sees one origin, cookies flow naturally),
# but these cover the cross-origin dev fallback: trust the local web origin as a
# CSRF referer and let CORS carry credentials.
CSRF_TRUSTED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
CORS_ALLOW_CREDENTIALS = True
