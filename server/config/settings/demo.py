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

# DEMO ONLY: serve uploaded media off the local filesystem (config.urls) and enable
# the upload endpoint. prod (DEBUG off) keeps this False — real prod serves media
# from S3/CDN, never through Django. Demo-grade like every other mock gate above;
# the deferred hardening gates in base.py STORAGES still apply before real serving.
SERVE_LOCAL_MEDIA = True
