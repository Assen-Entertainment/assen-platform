"""Disposable E2E settings: dev + the delivery checkout opened.

The live Playwright journey (.github/workflows/e2e.yml) exercises a physical
(goods) checkout end to end, which is gated off by default (ASS-287 A-1). This
harness profile inherits dev and flips ``ENABLE_SHIPPING_CHECKOUT`` on so that
flow can run — production/base/demo keep it hardcoded False. This is a test
harness, never a deployable profile.
"""

from __future__ import annotations

from config.settings.dev import *  # noqa: F403

# Open the delivery checkout for the live journey only (see module docstring).
ENABLE_SHIPPING_CHECKOUT = True
