"""Upload tracking model — who uploaded which media object (R11).

Records only the server-minted media URL, the magic-byte-validated content-type,
the owning account, and a timestamp. It deliberately stores NO user-supplied
filename (path-traversal / PII surface) and no file bytes — the bytes live in the
storage backend (local FS mock now, S3 후행), keyed by an unguessable UUID name.

Migrated app — ``migrate`` applies ``0001_initial``; regenerate with
``makemigrations`` when models change.
"""

from __future__ import annotations

import uuid

from django.db import models


class Upload(models.Model):
    """A single uploaded media object (image), tracked for ownership/audit."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        "identity.Account", on_delete=models.CASCADE, related_name="uploads"
    )
    # Server-minted, site-relative media URL (``/media/uploads/<uuid>.<ext>``). Never
    # a user filename — the UUID name is what defeats path traversal and PII leakage.
    # Reused verbatim as a Post/Product ``media_url`` (passes _validated_media_url).
    url = models.CharField(max_length=500)
    # The image content-type confirmed by the magic-byte sniff (e.g. "image/png") —
    # NOT the (spoofable) client-declared one.
    content_type = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Identify the upload by its id (never a user filename)."""
        return f"upload:{self.id}"
