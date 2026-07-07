"""Development settings: DEBUG on, eager-friendly Celery, local hosts."""

from __future__ import annotations

from config.settings.base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Serve uploaded media off the local filesystem (config.urls) and enable the upload
# endpoint — dev has no S3 backend, so local serving is the whole media path here.
SERVE_LOCAL_MEDIA = True

# Fan signup uses the deterministic mock OTP locally (no SMS provider wired).
ENABLE_MOCK_FAN_OTP = True

# R3 gated features opt in locally: the mock KYC verifier + mock payment tokenizer
# are wired, and 19+ read exposure is on so the age-gate/blur flows can be exercised
# against seeded adult items. All three are mock/skeleton — no real provider, PG, or
# real adult content is involved (production keeps these False; see base.py).
ENABLE_MOCK_KYC = True
ENABLE_ADULT_CONTENT = True
ENABLE_MOCK_PAYMENT = True

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
