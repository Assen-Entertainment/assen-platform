"""Upload moderation services — report-driven takedown (대표 approved 07-18).

The platform's minimum viable moderation posture for user-uploaded images is
*report-driven human moderation*, not automated scanning: an image is accepted once
it passes the hard image validation (apps.uploads.api), is reportable through the
existing safety domain (apps.safety), and an operator can take it down. Automated
provider scanning (nudity/CSAM) stays a 후행 대표·법무 gate.

This module owns the takedown half. It is called from
``apps.safety.services.change_report_status`` when a report about an upload reaches
``actioned`` — the safety app remains the single moderation domain (queue, RBAC,
audit, append-only status), and this is only the effect that domain applies to media.

Takedown is a **move, never a delete**
--------------------------------------
The status flip is what a request-time check reads: every media byte is served by
Django's gated view (apps.uploads.media) on every backend, so flipping ``status`` does
stop the image at the front door, immediately and without a cache purge. That is the
first line, and it is the reason media is proxied through Django at all.

The *move* is the second line, and it is not redundant. The status check can only
refuse a key it can resolve back to a row, so anything that reaches the bytes by
another route — a pre-signed URL minted by an operator tool, a bucket-direct read, a
row whose URL predates the current scheme — is answered only by the object no longer
being where it was. So a takedown also moves the stored object out of its served key
into a quarantine key (:func:`quarantine_key_for`): the served key then 404s in the
store itself, which invalidates every outstanding signed URL to it at once (a signed
URL grants access to a key, and there is nothing at that key any more). The bytes
survive at the quarantine key, so the safety domain's append-only / human-reversible
invariant holds: an operator mis-click is undoable (:func:`restore_upload`).

The move goes through Django's storage API (``default_storage``), so one code path
covers both the local FileSystemStorage (dev/test) and S3 (prod). No call site knows
the backend — the same reason the write site does not (apps.uploads.api).

Ordering and failure semantics (the storage move is NOT transactional with the DB)
---------------------------------------------------------------------------------
Both directions are ordered so that **every failure leaves the content not served**.
That is the fail-safe direction for moderation: a taken-down image that is still
reachable is a safety incident, while an image that is down when the DB says
otherwise is a broken image — recoverable, and visibly unfinished work.

- **Takedown** moves the object *before* the DB write, eagerly, inside the caller's
  transaction. If the move fails, it raises and the transaction rolls back: the report
  stays un-actioned and the image stays served (nothing ever claims a takedown that
  did not happen). If the move succeeds but the transaction later rolls back, the
  bytes are already out of the served key while the row still says ``visible`` — the
  safe mismatch, and a self-healing one (see below).
- **Restore** moves the object back only on ``transaction.on_commit``, i.e. *after*
  the DB write is durable. A rolled-back restore therefore never puts the bytes back,
  and a failed move-back leaves the row ``visible`` with the object still quarantined
  — again content-stays-down, and again self-healing.

Self-healing rather than silent: both functions reconcile the storage on **every**
call and only the DB write/audit are conditional, so re-running the operator action
converges on the correct state instead of short-circuiting on a stale row. This works
because the quarantine key is a deterministic function of the served key rather than
whatever ``save()`` happened to return — a rolled-back row must not be the only record
of where the bytes went.

Deployment follow-up (not fixable here): serving through Django is what keeps a
takedown immediate — there is no edge copy to purge. Should a CDN ever be put in front
of the media route, it can hold an already-fetched copy and keep serving it after the
status flip, and a purge-on-takedown becomes a hard requirement rather than an open
infra decision. Both the stored objects (``CacheControl: private, max-age=300``,
config.settings.base) and the served responses (apps.uploads.media) are marked
``private``, which keeps shared caches out today.
"""

from __future__ import annotations

from urllib.parse import unquote, urlparse

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.identity.models import Account
from apps.uploads.models import Upload, UploadStatus

# Key prefix the bytes of a taken-down object are moved under. Deliberately outside
# the ``uploads/`` prefix the served keys live in, so "is this object quarantined?" is
# answerable from the key alone — by us, by an operator reading the bucket, and by the
# local media route, which refuses the whole prefix (is_taken_down_media_path).
QUARANTINE_PREFIX = "quarantine/"


class UploadStorageError(RuntimeError):
    """Raised when a moderation move cannot be completed safely.

    Deliberately loud: every caller runs inside the safety app's transaction, so
    raising rolls the moderation decision back rather than recording a takedown or a
    restore that the storage never actually performed.
    """


def served_object_key(url: str) -> str:
    """The storage key ``url`` was minted from — the inverse of :func:`media_url_for_key`.

    Today's rows answer this trivially: ``url`` is ``MEDIA_URL`` + key on every backend
    (:func:`media_url_for_key`), so dropping the prefix returns the key.

    The absolute-URL branch is the **back-compat path**. Rows minted before the URL
    scheme was stabilised hold whatever ``default_storage.url()`` returned, which on S3
    is an absolute, signed, expiring
    ``https://<bucket>.s3.<region>.amazonaws.com/uploads/<uuid>.png?X-Amz-...`` — whose
    path is the key and whose signature rides in the query string ``urlparse``
    discards. Inverting those too costs one ``lstrip`` and keeps a takedown able to
    find the object behind any row ever written, so it stays.

    Derived from ``url`` rather than stored as its own column because ``url`` is never
    mutated and every row already has one — one code path, no backfill, and no second
    field that can drift out of agreement with the first about where the object is.
    """
    path = unquote(urlparse(url).path)
    media_path = urlparse(settings.MEDIA_URL).path
    if media_path and path.startswith(media_path):
        return path[len(media_path) :]
    return path.lstrip("/")


def quarantine_key_for(served_key: str) -> str:
    """The key a taken-down object at ``served_key`` is moved to.

    A pure function of the served key (which contains an unguessable UUID, so the
    quarantine key is unique too). Being deterministic — not a stored, backend-assigned
    name — is what lets a half-completed takedown be recognised and finished on retry.
    """
    return f"{QUARANTINE_PREFIX}{served_key}"


def _move_object(*, source: str, destination: str, content_type: str) -> None:
    """Move a stored object from ``source`` to ``destination`` via the storage API.

    Read → ``save()`` → ``delete()``: the only sequence the ``Storage`` interface
    offers, and therefore the one that behaves identically on the local filesystem and
    on S3. (django-storages' S3 backend has no ``copy_object`` seam exposed through
    this interface; reaching past it into boto3 would give the bucket a faster path at
    the cost of breaking dev/test entirely, so the storage API stays the default.)

    Idempotent, because it is re-run on every takedown/restore to reconcile a move
    whose DB write was lost:

    - source gone → the move already happened (or the object never existed); nothing
      to do, and the destination is authoritative.
    - both present → a previous attempt saved but did not finish deleting the source.
      Same object, so the destination already holds identical bytes; finish by
      dropping the source rather than re-writing it (``file_overwrite=False`` would
      mangle the key on a re-save and strand the bytes somewhere undeterministic).

    Never deletes an object it did not just create: the source is removed only once
    the destination is known to hold it.
    """
    if not default_storage.exists(source):
        return
    if default_storage.exists(destination):
        default_storage.delete(source)
        return

    with default_storage.open(source, "rb") as handle:
        content = ContentFile(handle.read())
    # Pin the re-written object's Content-Type to the row's sniff-derived type, exactly
    # as the write site does (apps.uploads.api). Without it the S3 backend would fall
    # back to guessing from the key's extension and a restored WEBP would come back as
    # application/octet-stream — see apps/uploads/test_s3_hardening.py.
    content.content_type = content_type  # type: ignore[attr-defined]
    saved = default_storage.save(destination, content)
    if saved != destination:
        # The destination was free a moment ago, so a backend that renamed it means a
        # racing writer took the key. Undo our copy and fail: bytes under a key nothing
        # records are worse than a moderation action the operator can simply retry.
        default_storage.delete(saved)
        raise UploadStorageError("quarantine key was taken by a concurrent write")
    default_storage.delete(source)


def take_down_upload(*, upload: Upload, actor: Account, report_id: str = "") -> Upload:
    """Stop serving ``upload`` — move the object to quarantine — and record who/why.

    The move runs first and unconditionally (see the module docstring): the bytes must
    leave the served key before anything claims they have, and re-reconciling on every
    call is what makes a takedown whose DB write was lost converge on retry instead of
    short-circuiting on the stale row.

    Idempotent: re-actioning a report about an already-taken-down image is a no-op
    rather than an error, because an image can legitimately attract several reports
    and the second operator to act must not hit a failure for doing the right thing.
    The no-op adds no second audit entry — the takedown happened once.

    Raises :class:`UploadStorageError` (or the backend's own error) if the object
    cannot be moved, which rolls the caller's transaction back and leaves the image
    served and the report un-actioned rather than recording a takedown that did not
    take effect.
    """
    served_key = served_object_key(upload.url)
    quarantine_key = quarantine_key_for(served_key)
    _move_object(
        source=served_key,
        destination=quarantine_key,
        content_type=upload.content_type,
    )
    if upload.is_taken_down and upload.quarantine_key == quarantine_key:
        return upload
    was_taken_down = upload.is_taken_down
    upload.status = UploadStatus.TAKEN_DOWN.value
    upload.quarantine_key = quarantine_key
    upload.save(update_fields=["status", "quarantine_key"])
    if not was_taken_down:
        record_audit(
            actor=actor,
            action=AuditAction.UPLOAD_TAKEN_DOWN.value,
            target=str(upload.id),
            # Ids only — never a narrative. The "why" lives in the report's restricted
            # detail store, reachable (manager+, audited) via this id.
            metadata={"safety_report_id": report_id} if report_id else {},
        )
    return upload


def restore_upload(*, upload: Upload, actor: Account, report_id: str = "") -> Upload:
    """Serve ``upload`` again — move the object back out of quarantine — and audit it.

    The inverse of :func:`take_down_upload`, and the reason a takedown moves bytes
    instead of deleting them: an operator who actioned the wrong report must be able
    to undo it with no data loss.

    Mirror-image ordering (see the module docstring): the DB write happens inside the
    caller's transaction but the move back is deferred to ``transaction.on_commit``,
    so a restore that rolls back never re-exposes the image. If the deferred move then
    fails, it raises after a durable ``visible`` row — the served key stays empty, so
    the image stays down (broken, not re-exposed) and re-running the un-action
    reconciles it.

    Idempotent: the move-back is re-attempted on every call (harmlessly — it is a
    no-op once the object is back), while the DB write and the audit entry happen only
    on the actual taken_down→visible transition.
    """
    served_key = served_object_key(upload.url)
    quarantine_key = upload.quarantine_key or quarantine_key_for(served_key)
    content_type = upload.content_type
    was_taken_down = upload.is_taken_down

    if was_taken_down or upload.quarantine_key:
        upload.status = UploadStatus.VISIBLE.value
        upload.quarantine_key = ""
        upload.save(update_fields=["status", "quarantine_key"])
    if was_taken_down:
        record_audit(
            actor=actor,
            action=AuditAction.UPLOAD_RESTORED.value,
            target=str(upload.id),
            metadata={"safety_report_id": report_id} if report_id else {},
        )
    transaction.on_commit(
        lambda: _move_object(
            source=quarantine_key,
            destination=served_key,
            content_type=content_type,
        )
    )
    return upload


def media_url_for_key(key: str) -> str:
    """The stable, site-relative media URL a stored object at ``key`` is served at.

    The single minter of ``Upload.url`` (apps.uploads.api) and the single way the media
    route maps a request back to its row — one function, so the two can never disagree
    about what a key's URL is.

    Deliberately **not** ``default_storage.url()``: that is backend-specific and, on
    S3 with ``querystring_auth``, returns a *signed URL that expires in an hour*.
    Persisting one of those (and copying it into a Post/Product ``media_url``) broke
    every production image roughly an hour after upload. This value is a pure function
    of the key, so it is identical on the local filesystem and on S3 and never goes
    stale. Django guarantees ``MEDIA_URL`` ends in a slash.
    """
    return f"{settings.MEDIA_URL}{key}"


def upload_for_media_key(key: str) -> Upload | None:
    """The :class:`Upload` row a media request for ``key`` resolves to, if any.

    Reconstructing the exact stored string — rather than matching on a suffix — keeps
    this an indexed equality read (``Upload.Meta.indexes``) and cannot collide across
    prefixes.

    None is a real answer, not an error: media predating the Upload table (fixtures,
    seeded demo images) has no row, and so does anything minted under the legacy
    absolute-signed scheme, whose stored ``url`` no request path can reconstruct. The
    media route treats a rowless object as unvouched-for rather than unavailable — see
    apps.uploads.media. (A legacy signed row is still fully moderatable: takedown
    inverts its ``url`` via :func:`served_object_key` and moves the bytes, so the
    served key 404s in the store regardless of what the row lookup can find.)
    """
    return Upload.objects.filter(url=media_url_for_key(key)).first()


def is_taken_down_media_path(path: str) -> bool:
    """Whether the media request ``path`` must not be served.

    Two ways to be unavailable:

    - the path is in quarantine. Takedown moves the object under
      :data:`QUARANTINE_PREFIX`, which lives inside the same store the served keys do
      and would otherwise be servable at a key trivially derivable from the original —
      handing back exactly the image an operator just removed. The quarantine location
      is never served, and no row lookup is needed to know that.
    - the path resolves to an :class:`Upload` row an operator has taken down. This is
      now the *primary* control rather than belt-and-braces: Django serves every media
      byte, so a status flip stops the image at the front door on every backend, with
      no cache to purge. (The takedown's object move independently 404s the key in the
      store; the two agree, which is the point.)

    Unknown paths are NOT taken down: media with no row must not be blanket-404'd.
    Takedown is asserted only for a row that actually says so.
    """
    if path.startswith(QUARANTINE_PREFIX):
        return True
    return Upload.objects.filter(
        url=media_url_for_key(path),
        status=UploadStatus.TAKEN_DOWN.value,
    ).exists()
