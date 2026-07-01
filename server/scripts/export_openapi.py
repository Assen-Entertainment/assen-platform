"""Export the backend OpenAPI schema to web/src/lib/api/openapi.json (SDLC 09 B5).

Keeps the committed ``openapi.json`` (and, after ``npm run gen:types``, the
generated ``schema.d.ts``) in sync with the live Django Ninja B2 API — so the
web contract types are derived from the backend, not hand-maintained.

    # Windows
    server\\.venv-win\\Scripts\\python server\\scripts\\export_openapi.py
    # then
    cd web && npm run gen:types
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_DIR = REPO_ROOT / "server"
OUT = REPO_ROOT / "web" / "src" / "lib" / "api" / "openapi.json"

sys.path.insert(0, str(SERVER_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")

import django  # noqa: E402

django.setup()

from config.api import api  # noqa: E402

schema = api.get_openapi_schema()
OUT.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"wrote {OUT.relative_to(REPO_ROOT)} ({len(schema['paths'])} paths)")
