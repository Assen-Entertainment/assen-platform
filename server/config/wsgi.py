"""WSGI entry point used by gunicorn.

Requires ``DJANGO_SETTINGS_MODULE`` to be set explicitly — no dev fallback
(ASS-285), so a deployment that omits it fails loudly instead of booting dev.
"""

from __future__ import annotations

from django.core.wsgi import get_wsgi_application

from config.require_settings import require_settings_module

require_settings_module()

application = get_wsgi_application()
