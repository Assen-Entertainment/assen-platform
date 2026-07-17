"""Upload tracking model — who uploaded which media object (R11).

Records only the server-minted media URL, the magic-byte-validated content-type,
the owning account, a serving status, and a timestamp. It deliberately stores NO
user-supplied filename (path-traversal / PII surface) and no file bytes — the bytes
live in the storage backend (local FS in dev/demo/test, S3 in prod), keyed by an
unguessable UUID name.

``status`` carries the report-driven moderation posture: an upload an operator has
actioned a safety report against is ``taken_down`` and stops being served, but the
row is never deleted (safety-app invariant). Stopping the *serving* means moving the
stored object to a quarantine key — recorded in ``quarantine_key`` — never deleting
the bytes; see :mod:`apps.uploads.services`.

Migrated app — ``migrate`` applies ``0001_initial``; regenerate with
``makemigrations`` when models change.
"""

from __future__ import annotations

import uuid

from django.db import models


class UploadStatus(models.TextChoices):
    """Serving lifecycle for an upload — taken down, never deleted.

    Mirrors the safety app's invariant (a report/block changes ``status`` and is
    never removed) so the audit trail survives: the row, its owner, and the report
    that led to the takedown all stay reconstructable afterwards.
    """

    VISIBLE = "visible", "visible"
    TAKEN_DOWN = "taken_down", "taken_down"


class Upload(models.Model):
    """A single uploaded media object (image), tracked for ownership/audit."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        "identity.Account", on_delete=models.CASCADE, related_name="uploads"
    )
    # Server-minted, STABLE, site-relative media URL: ``{MEDIA_URL}uploads/<uuid>.<ext>``
    # (apps.uploads.services.media_url_for_key), identical on the local filesystem and
    # on S3 because it is a pure function of the storage key. Django serves the bytes
    # back at it on every backend (apps.uploads.media).
    #
    # NOT ``default_storage.url()``: on S3 with querystring_auth that returns a SIGNED
    # url that expires in ~1h. Persisting one — as this column briefly did — broke every
    # image roughly an hour after upload, because the value is durable: it is reused
    # verbatim as a Post/Product ``media_url`` (it passes _validated_media_url). A URL
    # stored in a row must not have a lifetime.
    #
    # Never a user filename — the UUID name is what defeats path traversal and PII
    # leakage. NEVER mutated: it is the record of the served key a takedown moved the
    # object away from, and therefore what a restore moves it back to
    # (apps.uploads.services.served_object_key derives that key from it — including,
    # for back-compat, from a legacy absolute signed URL).
    url = models.CharField(max_length=500)
    # The image content-type confirmed by the magic-byte sniff (e.g. "image/png") —
    # NOT the (spoofable) client-declared one.
    content_type = models.CharField(max_length=64)
    # Report-driven human moderation (대표 approved 07-18): an operator taking a
    # safety report about this object to ACTIONED flips this to ``taken_down``, after
    # which the media route refuses to serve it (apps.uploads.media.serve_upload) AND
    # the stored object is moved to ``quarantine_key`` so the served key stops
    # resolving in the bucket too. The bytes and the row are both kept — takedown is a
    # status change plus a move, never a delete.
    status = models.CharField(
        max_length=16,
        choices=UploadStatus.choices,
        default=UploadStatus.VISIBLE,
    )
    # Where the bytes went when this upload was taken down (``quarantine/uploads/
    # <uuid>.<ext>``); empty while visible. Recorded rather than only recomputed so a
    # restore is deterministic and an operator can locate the object of a takedown
    # whose key scheme has since changed. The value is derivable from ``url`` by
    # design (apps.uploads.services.quarantine_key_for) — that redundancy is what lets
    # a takedown whose DB write was lost self-heal on retry rather than strand bytes
    # under a key nothing records.
    quarantine_key = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "-created_at"]),
            # The media route resolves a request path back to its row on every served
            # image to check ``status``; without this that read is a full scan.
            models.Index(fields=["url"]),
        ]
        ordering = ["-created_at"]

    @property
    def is_taken_down(self) -> bool:
        """Whether this object has been taken down and must not be served."""
        return self.status == UploadStatus.TAKEN_DOWN.value

    def __str__(self) -> str:
        """Identify the upload by its id (never a user filename)."""
        return f"upload:{self.id}"
