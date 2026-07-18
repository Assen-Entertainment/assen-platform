"""DEMO ONLY settings — every mock gate ON atop production hardening (R11).

╔════════════════════════════════════════════════════════════════════════════╗
║  DEMO DEPLOYMENT ONLY — DO NOT SERVE REAL USERS OR REAL MONEY.              ║
║                                                                            ║
║  Inherits everything from prod (DEBUG off, security headers, fail-closed   ║
║  required env, JSON logging, Sentry) and then flips all FOUR mock gates ON ║
║  so a demo instance can walk the entire flow — login OTP, payment, KYC,    ║
║  19+ content — end to end with deterministic MOCK services and no real     ║
║  provider wired. Those mocks are unverifiable (anyone can reproduce their  ║
║  codes/tokens), so this profile must never back real accounts or charges.  ║
║  Real payment/KYC integrations remain unimplemented — mock services only.  ║
╚════════════════════════════════════════════════════════════════════════════╝

Selected with ``DJANGO_SETTINGS_MODULE=config.settings.demo`` for a demo host;
prod (config.settings.prod) is unchanged and keeps every gate OFF (base.py).
"""

from __future__ import annotations

from config.settings.prod import *  # noqa: F403

# DEMO ONLY: enable every mock gate. base.py hardcodes these False and prod inherits
# that; only this demo profile (and dev/test) opt in. No real provider/PG/adult
# activation happens — the services behind these flags are mocks/skeletons.
ENABLE_MOCK_FAN_OTP = True
ENABLE_MOCK_KYC = True
ENABLE_MOCK_PAYMENT = True
ENABLE_ADULT_CONTENT = True
ENABLE_MOCK_PUSH = True
ENABLE_MOCK_SOCIAL_AUTH = True
# DEMO ONLY: mock (log-only) email sender so the email+password flow is walkable. The
# verification token is NOT echoed in the response by default (EMAIL_VERIFY_RETURN_TOKEN
# defaults False, inherited from base) — a demo operator reads it from the logs, keeping
# the token off the wire in this prod-hardened profile. A non-prod host on this profile
# (e.g. dev) may set EMAIL_VERIFY_RETURN_TOKEN=1 in env to echo it for automated e2e.
ENABLE_MOCK_EMAIL = True

# Accept uploads in the demo. The only difference from production is the storage
# backend underneath (local filesystem here, S3 there — DJANGO_MEDIA_S3_BUCKET): the
# accept gate, the URL scheme, and the serving route are identical, so the demo walks
# the same media path prod does. The deferred hardening gates in base.py STORAGES still
# apply.
ALLOW_UPLOADS = True
