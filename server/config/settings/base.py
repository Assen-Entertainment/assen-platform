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

# Email + password fan auth (now a primary login — phone OTP was removed). The mock
# email sender (config.email) logs the verification mail instead of delivering it —
# anyone could read the log and complete a verification — so it is dev/test/demo only.
# Hardcoded False here (NOT env-driven), exactly like ENABLE_MOCK_FAN_OTP, so a stray
# production env var cannot enable a mock in prod. It stays False here; production
# instead selects a REAL adapter via EMAIL_SENDER_BACKEND below, and still fails closed
# (503) rather than pretend a mail was sent when none is configured.
ENABLE_MOCK_EMAIL: bool = False

# --- Real email transport (config.email) --------------------------------------
# The mock above can never run in prod, so these select the REAL sender: an AWS SES
# (boto3 SESv2) or a generic SMTP adapter. Seam pattern (as in config.payment): the
# adapter code ships, while the provider setup (SES identity verification + sandbox
# exit, or an SMTP relay account) stays an external credential gate. Env-driven and
# EMPTY by default, so nothing changes until a deployment supplies real values.
# FAIL-CLOSED: an unset, unknown, OR partially configured backend leaves
# config.email.email_sender() at None and the email-auth surface 503s — never a
# half-working sender. (prod additionally refuses to boot on an unknown backend name,
# which could otherwise 503 silently forever; see config/settings/prod.py.)
#
# - EMAIL_SENDER_BACKEND: "ses" | "smtp" | "" (none). Anything else = none.
# - EMAIL_FROM_ADDRESS: the From: address of the verification mail (both backends).
#   Must be an SES-verified identity when the backend is "ses".
# - EMAIL_REPLY_TO_ADDRESS: OPTIONAL Reply-To: of the verification mail (both backends).
#   Empty (the default) → no Reply-To header, i.e. unchanged behavior. NOT part of the
#   fully-configured gate — a sender is valid with or without it, so its absence never
#   triggers the 503 fail-closed path. Set it (e.g. contact@assenent.com) so a fan who
#   replies reaches a real inbox instead of the no-reply From: box.
# - WEB_BASE_URL: origin of the WEB app the verify link points at
#   ({WEB_BASE_URL}/verify-email?token=…) — the fan lands on a page, which then calls
#   the confirm endpoint. Required by both backends: without it the mail could carry no
#   usable link, so its absence fails closed too.
EMAIL_SENDER_BACKEND: str = env("EMAIL_SENDER_BACKEND", default="")
EMAIL_FROM_ADDRESS: str = env("EMAIL_FROM_ADDRESS", default="")
EMAIL_REPLY_TO_ADDRESS: str = env("EMAIL_REPLY_TO_ADDRESS", default="")
WEB_BASE_URL: str = env("WEB_BASE_URL", default="")

# AWS SES (EMAIL_SENDER_BACKEND=ses). Only the region is configured: boto3 signs with
# the ambient AWS chain (the ECS task role), so NO static access key is read or stored.
# Region default mirrors DJANGO_MEDIA_S3_REGION below.
EMAIL_SES_REGION: str = env("EMAIL_SES_REGION", default="ap-northeast-2")

# Generic SMTP (EMAIL_SENDER_BACKEND=smtp) — Django's own mail-stack settings, which
# config.email.SmtpEmailSender uses through django.core.mail (EMAIL_BACKEND stays
# Django's SMTP default; the test suite swaps in locmem). EMAIL_HOST is the activation
# key: empty → the backend is unconfigured and email_sender() returns None. User/
# password stay optional (an IP-allowlisted relay needs neither). EMAIL_TIMEOUT bounds
# a hung relay so one signup cannot tie up a worker indefinitely.
EMAIL_HOST: str = env("EMAIL_HOST", default="")
EMAIL_PORT: int = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER: str = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD: str = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS: bool = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL: bool = env.bool("EMAIL_USE_SSL", default=False)
EMAIL_TIMEOUT: int = env.int("EMAIL_TIMEOUT", default=10)

# Email-verification token lifetime (seconds). The signed confirm token
# (config.email.make_verification_token) is valid for this window; 24h default.
EMAIL_VERIFY_TTL_SECONDS: int = env.int("EMAIL_VERIFY_TTL_SECONDS", default=86400)

# Dev/QA affordance: when on, the /fan/signup/email response echoes the signed
# verification token so e2e/QA can complete the confirm step without a real inbox.
# Hardcoded False here (never leak the token in prod/demo); only dev/test opt in.
EMAIL_VERIFY_RETURN_TOKEN: bool = False

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
# - ENABLE_MOCK_SOCIAL_AUTH: the deterministic mock social-login provider
#   (config.social_auth). Off → /fan/social/* fails closed (503); no real Kakao/Google/
#   Naver OAuth app is wired (a credential gate). dev/test/demo opt in.
ENABLE_MOCK_SOCIAL_AUTH: bool = False

# Real social OAuth credentials (empty = that provider uses the mock / is unavailable).
# Set per-env (prod: Secrets Manager; local test: a local .env). config.social_auth
# activates a provider's REAL adapter only when BOTH its id and secret are present, so
# a partial config is explicit. These are read here (schema-full env) so dev/test with
# nothing set keep the mock; a stray value never silently changes behaviour.
SOCIAL_KAKAO_CLIENT_ID = env("SOCIAL_KAKAO_CLIENT_ID", default="")
SOCIAL_KAKAO_CLIENT_SECRET = env("SOCIAL_KAKAO_CLIENT_SECRET", default="")
SOCIAL_GOOGLE_CLIENT_ID = env("SOCIAL_GOOGLE_CLIENT_ID", default="")
SOCIAL_GOOGLE_CLIENT_SECRET = env("SOCIAL_GOOGLE_CLIENT_SECRET", default="")
SOCIAL_NAVER_CLIENT_ID = env("SOCIAL_NAVER_CLIENT_ID", default="")
SOCIAL_NAVER_CLIENT_SECRET = env("SOCIAL_NAVER_CLIENT_SECRET", default="")

# Social login OAuth state: signed httpOnly cookie TTL (anti-CSRF, binds callback to the
# browser session that started the flow). Cross-worker safe (no server store).
SOCIAL_STATE_TTL_SECONDS: int = env.int("SOCIAL_STATE_TTL_SECONDS", default=600)
# Optional allowlist of redirect_uri ORIGINS (scheme://host[:port]). Empty = rely on the
# state-cookie redirect binding as the primary defense; configure in prod to lock down.
SOCIAL_ALLOWED_REDIRECT_ORIGINS: list[str] = env.list("SOCIAL_ALLOWED_REDIRECT_ORIGINS", default=[])

# Push-notification transport gate (#16 P5). The operator push-dispatch surface
# uses an in-memory mock adapter (apps.notification.adapters) — no real FCM/APNs is
# wired. Hardcoded False here (NOT env-driven), so production fails closed (503
# PushUnavailable) rather than pretend a push was delivered; only dev/test/demo opt
# in. A real transport replaces the mock behind this same flag in P5.
ENABLE_MOCK_PUSH: bool = False

# Delivery (shipping-address) checkout — OFF until the postal-shipping privacy
# policy is approved (ASS-287 A-1). While off, any physical (goods) order is
# refused (503 SHIPPING_CHECKOUT_UNAVAILABLE) so NO recipient name/phone/address
# PII is collected. Hardcoded (never read from env) so a stray env cannot open
# PII collection in base/prod/demo; dev inherits this False, and test.py + the
# disposable e2e settings turn it on to exercise the flow.
ENABLE_SHIPPING_CHECKOUT: bool = False

# Data-retention sweep master switch (Codex #19, 법무 게이트). FAIL-CLOSED: default
# False so the nightly sweep (apps.identity.tasks.run_retention_sweep) only COUNTS the
# rows past each retention window and logs them — it deletes/blanks NOTHING — until a
# deployment deliberately turns it on. Env-overridable so a vetted environment can
# enable the safe hygiene purges without a code change; base/prod stay False until
# legal signs off on the real windows.
RETENTION_PURGE_ENABLED: bool = env.bool("RETENTION_PURGE_ENABLED", default=False)

# Per-class retention windows in DAYS. CONSERVATIVE PLACEHOLDERS ONLY — 법무 will set
# the real statutory windows (전자상거래법 거래·분쟁 기록 5년/3년, 탈퇴계정 보존기간 등);
# do NOT treat these as approved retention periods.
# - RETENTION_WITHDRAWN_ACCOUNT_DAYS: age of an already-anonymised withdrawn Account
#   (Account.withdrawn_at) before its DEFERRED final purge. The sweep only COUNTS these
#   — the row deletion stays unimplemented until legal (apps.identity.retention).
# - RETENTION_TOKEN_DAYS: age of a fully expired/revoked TokenFamily before hygiene
#   deletion (no PII, pure auth-state cleanup; actually deleted when the flag is on).
# - RETENTION_SHIPPING_SNAPSHOT_DAYS: age of a COMPLETED/CANCELLED Order before its
#   recipient_*/address delivery snapshot is BLANKED (the order row itself is kept).
RETENTION_WITHDRAWN_ACCOUNT_DAYS: int = env.int("RETENTION_WITHDRAWN_ACCOUNT_DAYS", default=30)
RETENTION_TOKEN_DAYS: int = env.int("RETENTION_TOKEN_DAYS", default=90)
RETENTION_SHIPPING_SNAPSHOT_DAYS: int = env.int("RETENTION_SHIPPING_SNAPSHOT_DAYS", default=180)

# Hosted-commerce bridge (apps.commerce_bridge) — the integration seam for a hosted
# commerce SaaS (Cafe24/아임웹) if the platform adopts the "hosted commerce + custom
# fan platform" hybrid. OFF by default and hardcoded here (never env in base) so the
# inbound webhook fails closed (503) unless a deployment deliberately enables it AND
# supplies a signing secret. Keeping it wired-but-off means BOTH tracks (full custom
# vs hybrid) stay viable without re-architecting.
ENABLE_COMMERCE_BRIDGE: bool = False

# HMAC signing secret for inbound hosted-commerce webhooks. Empty → every webhook is
# rejected (fail-closed), even when ENABLE_COMMERCE_BRIDGE is on. Set per-provider in
# the deployment env; never committed.
COMMERCE_BRIDGE_WEBHOOK_SECRET: str = ""

# Per-user rate limiting on the fan write endpoints (follow/like/comment/post,
# SDLC 09 §4, E11/B4). On by default so dev/prod throttle real traffic; the test
# suite turns it off (config/settings/test.py) to stay deterministic across the
# many writes it fires for one fixture account. Env-overridable (default True, so
# prod stays throttled) for rapid smoke/load runs that fire many writes at once.
# See config.throttle.
FAN_WRITE_THROTTLE_ENABLED: bool = env.bool("FAN_WRITE_THROTTLE_ENABLED", default=True)

# Dedicated HMAC key for the phone-identifier hash (Account.auth_subject_hash) —
# separate from SECRET_KEY (ASS-287 A-2). Keying the hash means a stolen DB alone
# cannot brute-force the small phone-number space. dev/test/demo carry an insecure,
# env-overridable default; production (config.settings.prod) REQUIRES a real
# >=32-byte key from the environment and fails closed at boot without it.
PHONE_IDENTIFIER_HMAC_KEY: str = env.str(
    "PHONE_IDENTIFIER_HMAC_KEY",
    default="dev-insecure-phone-identifier-hmac-key-not-for-prod",
)

# Rate-limiter backend for the cross-cutting middleware limiter (config.ratelimit).
# "memory" (default) is the per-process in-memory limiter; "redis" selects the shared
# cross-worker limiter (config.ratelimit.RedisRateLimiter). Default stays "memory" so
# dev/test need no Redis; prod opts into "redis" via env. If "redis" is selected but
# Redis is unreachable, get_rate_limiter fails safe to in-memory (never a SPOF).
RATELIMIT_BACKEND: str = env("RATELIMIT_BACKEND", default="memory")

# Redis connection for the shared rate limiter (used only when RATELIMIT_BACKEND=redis).
# A dedicated DB (…/2), distinct from Celery's broker (…/0) and result backend (…/1),
# so limiter keys never collide with task state on the same Redis instance.
RATELIMIT_REDIS_URL: str = env("RATELIMIT_REDIS_URL", default="redis://localhost:6379/2")

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
    # Migrated like the rest — each app ships `0001_initial`, applied by `migrate`.
    "apps.creator",
    "apps.social",
    "apps.content",
    "apps.commerce",
    "apps.membership",
    # Saved payment methods (R3): brand + last4 + mock PG token only — never a card
    # PAN/expiry/cvc. Migrated like the rest (`migrate` applies `0001_initial`).
    "apps.payments",
    # Hosted-commerce bridge — provider-agnostic integration seam (inbound webhook +
    # external order/settlement records) for a hosted commerce SaaS, fail-closed off.
    "apps.commerce_bridge",
    # Image uploads (R11): validated image → storage (local FS mock now, S3 후행).
    # Tracks only a server-minted media URL + content-type + owner (no filename/PII).
    # Migrated like the rest (`migrate` applies `0001_initial`).
    "apps.uploads",
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

# Content-Security-Policy, REPORT-ONLY (ASS-278). Observation-only hardening: sent
# as Content-Security-Policy-Report-Only (config.middleware.SecurityHeadersMiddleware),
# never the enforcing Content-Security-Policy header, so a bad policy string cannot
# break the site — the browser only logs/reports violations. The default baseline is
# admin-safe (Django admin's templates use inline <style>/<script>, hence the
# 'unsafe-inline' sources) since this server only renders JSON API responses plus the
# Django admin HTML. No report-uri/report-to is set by default — there is no
# violation-collection endpoint yet; set CONTENT_SECURITY_POLICY_REPORT_ONLY to a
# policy string that includes one once a collector exists. Env-tunable so it can be
# tightened (or disabled entirely via an empty string) without a code change; an
# empty/unset value means the middleware omits the header altogether (opt-out).
CONTENT_SECURITY_POLICY_REPORT_ONLY: str = env(
    "CONTENT_SECURITY_POLICY_REPORT_ONLY",
    default=(
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'self'; "
        "object-src 'none'"
    ),
)

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

# --- Media (user-uploaded images) ---------------------------------------------
# Uploaded images (avatars, post/product media) are written through Django's storage
# abstraction (STORAGES["default"]) so no call site knows the backend: the local
# filesystem under MEDIA_ROOT in dev/demo/test, S3 in production.
#
# Django SERVES media itself in every environment, on every backend (config.urls →
# apps.uploads.media), rather than handing out bucket-direct signed URLs. Two reasons,
# both load-bearing: a signed URL expires (~1h) while the URL we mint is persisted on
# the Upload row and copied into Post/Product media_url — so a stored image would break
# an hour after upload — and a bucket-direct read never reaches Django, so no takedown
# check could run on the only path production would use. Bandwidth through the app tier
# is the price; a CDN can front this later (see apps.uploads.services for what that
# would then oblige: purge-on-takedown).
#
# Values are env-tunable so a container can relocate the volume without a code change.
MEDIA_URL = env("DJANGO_MEDIA_URL", default="/media/")
MEDIA_ROOT = env("DJANGO_MEDIA_ROOT", default=str(BASE_DIR / "media"))

# Whether the upload endpoint accepts writes at all (apps.uploads.api fails closed
# with 503 + UPLOAD_STORAGE_UNAVAILABLE when this is off). Env-driven, default False
# so an unconfigured environment never takes untrusted bytes. This is the ONLY switch
# on the upload surface.
#
# Turning it ON is necessary but NOT sufficient: apps.uploads.api additionally requires
# that the storage backend can hold the object (config.storage.media_storage_ready —
# in practice, that an object-storage backend names a bucket). Accepting bytes that
# cannot come back is the original bug this gate exists to prevent.
#
# There used to be a second flag here, SERVE_LOCAL_MEDIA ("Django hands out bytes off
# the local disk"), which was retired when Django became the serving path everywhere:
# the question it answered is no longer a variable, and a flag whose answer is always
# yes is a comment pretending to be a gate.
ALLOW_UPLOADS: bool = env.bool("ALLOW_UPLOADS", default=False)

# Hard ceiling on a single uploaded file (bytes); 10 MiB default, env-tunable. The
# upload endpoint (apps.uploads.api) rejects anything larger BEFORE the bytes are
# read into memory or written to storage.
UPLOAD_MAX_BYTES: int = env.int("UPLOAD_MAX_BYTES", default=10 * 1024 * 1024)

# Decompression-bomb guards for the Pillow decode-verify step (ASS-271, see
# apps.uploads.images.verify_image_decodes) — both env-tunable. A file within
# UPLOAD_MAX_BYTES can still decode to a huge pixel buffer (e.g. a highly
# compressed PNG), so these bound the *decoded* image independently of file size:
# total pixel count (width * height) and either dimension individually.
UPLOAD_MAX_PIXELS: int = env.int("UPLOAD_MAX_PIXELS", default=40_000_000)
UPLOAD_MAX_DIMENSION: int = env.int("UPLOAD_MAX_DIMENSION", default=12_000)

# Django 5 storage backends. default = local filesystem for dev/demo/test; a real
# deployment sets DJANGO_MEDIA_S3_BUCKET (below) to route default_storage at a
# PRIVATE S3 bucket. Upload call sites use ``default_storage`` only, so the backend
# swap changes nothing else.
#
# GATES ON THE REAL (non-demo) UPLOAD + SERVING PATH. The upload surface has ONE
# switch — ALLOW_UPLOADS (accept writes) — and apps.uploads.api requires it *plus* a
# storage backend that can hold the object (config.storage.media_storage_ready) before
# it accepts a single byte:
#   1. DONE (ASS-271): full decode, not just a header sniff — apps.uploads.api
#      calls apps.uploads.images.verify_image_decodes after the 64-byte magic sniff,
#      which runs Pillow ``Image.open(...).verify()`` on the full payload plus a
#      UPLOAD_MAX_PIXELS/UPLOAD_MAX_DIMENSION decompression-bomb + dimension guard
#      (a valid polyglot outside the 64-byte sniff window is also defused today
#      because the served Content-Type is sniff-derived + X-Content-Type-Options:
#      nosniff).
#   2. DONE: object-storage hardening — the S3 block below pins a private bucket
#      (default_acl None; no ACL is ever sent), forces a non-executable
#      Content-Disposition via object_parameters, and the per-object Content-Type is
#      pinned at the write site from the magic-byte sniff (apps.uploads.api; see the
#      object_parameters comment below for why ContentType cannot live here). Reads do
#      NOT go to the bucket — Django serves them (apps.uploads.media), which is what
#      keeps a media URL stable and a takedown immediate; the bucket stays private so
#      the app tier is the only reader.
#   3. PARTIAL — report-driven human moderation (minimum posture, 대표 approved
#      07-18). Accepted images are reportable (apps.safety fan/operator report
#      intake takes an upload target) and an operator taking a report to ACTIONED
#      takes the upload down, after which the media route stops serving it on every
#      backend. Automated provider scanning (nudity/CSAM — Rekognition et al.) remains
#      후행 and is still a 대표·법무 gate; apps.uploads.api._moderation_accepts is its
#      plug-in seam.
STORAGES: dict[str, dict[str, object]] = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Real object storage (S3) — opt-in via env, behaviour-preserving when unset. Set
# DJANGO_MEDIA_S3_BUCKET to route default_storage to a PRIVATE S3 bucket
# (django-storages[s3]); call sites are unchanged (they use default_storage). Objects
# are private (the bucket blocks public access; no ACL) and nothing but the app tier
# reads them: media is served by Django (apps.uploads.media), not fetched from the
# bucket by the browser. Empty (default) keeps the local filesystem backend for
# dev/test. Setting this satisfies the storage half of the upload gate
# (config.storage.media_storage_ready — a bucket-less S3 backend does NOT); the accept
# half is ALLOW_UPLOADS, and automated moderation scanning (gate #3 above) remains 후행.
#
# querystring_auth below still governs default_storage.url(), which the upload path no
# longer calls — Upload.url is minted from the storage key instead
# (apps.uploads.services.media_url_for_key). It is kept True so that any *future* caller
# (an operator tool, a direct-download link) gets a signed URL against the private
# bucket rather than an unusable public-style one.
_media_s3_bucket = env("DJANGO_MEDIA_S3_BUCKET", default="")
if _media_s3_bucket:
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": _media_s3_bucket,
            "region_name": env("DJANGO_MEDIA_S3_REGION", default="ap-northeast-2"),
            "default_acl": None,
            "querystring_auth": True,
            "file_overwrite": False,
            "signature_version": "s3v4",
            # Gate #2 hardening. django-storages applies object_parameters to EVERY
            # object verbatim (S3Storage.get_object_parameters returns this dict
            # unchanged), so it can only carry values that are correct for all four
            # allowed raster families — which rules ContentType OUT: pinning one here
            # would stamp e.g. image/png onto a JPEG. The per-object ContentType is
            # therefore pinned at the write site from the magic-byte sniff
            # (apps.uploads.api sets ``ContentFile.content_type``, which
            # S3Storage._get_write_parameters reads), never from the client's claim.
            # django-storages' own fallback if that is ever bypassed is
            # ``default_content_type`` = application/octet-stream — inert, not HTML.
            #
            # ContentDisposition IS uniform, so it belongs here: "inline" renders the
            # image in the feed while (combined with the forced image/* ContentType and
            # the global X-Content-Type-Options: nosniff) denying the browser any route
            # to treat a stored object as HTML/script. Never "attachment" — these are
            # feed images, and an attachment disposition would break rendering without
            # adding safety the forced type + nosniff do not already provide.
            "object_parameters": {
                "ContentDisposition": "inline",
                # Gated media must not be cached by any shared proxy: a takedown has to
                # stop the image for everyone at once, and a shared cache would keep
                # handing out a copy the operator already removed. The media route sets
                # the same value on the responses it serves (apps.uploads.media), so the
                # posture holds whether the bytes are read from here or from Django.
                "CacheControl": "private, max-age=300",
            },
        },
    }

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
    # Mock subscription billing (Codex #5): expire ended cancelled subs and renew
    # active ones (mock settlement + advanced period). Idempotent per period, so the
    # daily cadence only ever settles a period once. No real gateway is called.
    "run-subscription-billing-cycle": {
        "task": "apps.membership.tasks.run_subscription_billing_cycle",
        "schedule": crontab(hour=3, minute=0),
    },
    # Nightly data-retention sweep (Codex #19), after the billing cycle. FAIL-CLOSED:
    # with RETENTION_PURGE_ENABLED off (default) it only counts + logs matched rows; on,
    # it runs the implemented per-class purges (token hygiene, shipping-snapshot
    # blanking) and still DEFERS the withdrawn-account final purge (법무 게이트).
    # Idempotent, so the daily cadence is safe to re-run.
    "run-retention-sweep": {
        "task": "apps.identity.tasks.run_retention_sweep",
        "schedule": crontab(hour=4, minute=0),
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
