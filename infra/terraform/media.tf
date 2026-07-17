# Media object storage (S3) — the private bucket behind DJANGO_MEDIA_S3_BUCKET.
#
# base.py routes STORAGES["default"] to storages.backends.s3.S3Storage when
# DJANGO_MEDIA_S3_BUCKET is set, with default_acl = None and querystring_auth = True.
# That settings block ASSERTS a private bucket ("objects are private (the bucket blocks
# public access; no ACL)") but cannot enforce it — the enforcement is here.
#
# Creation is opt-in (var.create_media_bucket, default false) and SEPARATE from
# var.media_s3_bucket, which merely NAMES the bucket the app and the task role use.
# The split is load-bearing: dev already runs against a bucket created out-of-band
# (dev.tfvars sets media_s3_bucket to an existing bucket), so a dev/staging apply must
# keep its IAM grant while creating nothing. create_media_bucket = false → every
# resource in this file has count = 0 → no-op for those environments.

resource "aws_s3_bucket" "media" {
  count  = var.create_media_bucket ? 1 : 0
  bucket = var.media_s3_bucket

  # count cannot express "create only if named", and an empty bucket name would fail
  # deep in the provider with an opaque error. Fail here with the actionable message.
  lifecycle {
    precondition {
      condition     = var.media_s3_bucket != ""
      error_message = "create_media_bucket = true requires media_s3_bucket to name the bucket (it is also the value of DJANGO_MEDIA_S3_BUCKET in container_environment)."
    }
  }
}

# The private half of the app's security model, made real. All four blocks on: no ACL
# and no bucket policy can ever make an object public, whatever a future change does.
# Nothing here needs public access: the app tier (the ECS task role) is the ONLY reader
# of this bucket. Media reaches browsers through Django's gated view (apps/uploads/media.py
# streams it after checking takedown status) — never bucket-direct, so no object ever
# needs to be fetchable by anyone but the task role.
resource "aws_s3_bucket_public_access_block" "media" {
  count                   = var.create_media_bucket ? 1 : 0
  bucket                  = aws_s3_bucket.media[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ACLs disabled entirely — the bucket owner owns every object. Consistent with the
# app's default_acl = None (django-storages sends no ACL header at all; with
# BucketOwnerEnforced an ACL header would be REJECTED, so the two must agree).
resource "aws_s3_bucket_ownership_controls" "media" {
  count  = var.create_media_bucket ? 1 : 0
  bucket = aws_s3_bucket.media[0].id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# Default encryption at rest. SSE-S3 (AES256) is the floor and costs nothing.
# NOTE: SSE-KMS with a CMK would be strictly better — it adds a second, auditable
# authorization gate (a key policy the task role must ALSO satisfy) and per-decrypt
# CloudTrail data events, which matters for user-uploaded media. It is not the default
# here because it needs a CMK + kms:Decrypt/GenerateDataKey on the task role, i.e. an
# account-level key decision that belongs to the first real apply, not to this default.
resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  count  = var.create_media_bucket ? 1 : 0
  bucket = aws_s3_bucket.media[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Versioning ON — the recovery net under the moderation MOVE path.
#
# Verified against the shipped code, not inferred: a moderation takedown
# (apps/uploads/services.py:take_down_upload) MOVES the object. It is not a status flip
# — apps/uploads/services.py:_move_object reads the source, saves it under the
# quarantine key, and then calls default_storage.delete(source); restore_upload runs
# the same move in reverse. So s3:DeleteObject (iam.tf) is not a dormant grant sitting
# next to an app that never deletes: it is on the hot path of every takedown and every
# restore, called by design, several times per moderation decision.
#
# That is precisely what versioning is here for. The safety domain's contract is that a
# takedown is human-reversible and the bytes are never destroyed — but that contract is
# implemented by a non-transactional read→save→delete against a remote store, and it is
# the delete half that makes it fallible. A mis-move, a bug in that path, or a delete
# that lands after a save that did not, would otherwise be gone bytes while the DB still
# claims the decision is undoable. Versioning turns every one of those into a
# recoverable delete marker, so the reversibility the moderation posture promises
# survives a fault in the code that implements it. Cheap insurance on the one path that
# can destroy user data; enabled deliberately on that basis.
#
# Storage consequence, stated honestly: because the delete half now really fires, a
# takedown leaves the bytes both at the quarantine key AND as a noncurrent version of
# the served key. Versioned storage is therefore ~2x for a taken-down object (~3x after
# a takedown→restore round trip) — bounded by moderation volume, not by traffic or
# upload volume, and it is the cost of the guarantee, not waste. Nothing accrues per
# read or per upload: the app never overwrites a key (S3Storage file_overwrite = False).
resource "aws_s3_bucket_versioning" "media" {
  count  = var.create_media_bucket ? 1 : 0
  bucket = aws_s3_bucket.media[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

# Lifecycle — deliberately ONE rule, and one that cannot touch live media.
#
# Aborting incomplete multipart uploads only ever reclaims parts of uploads that never
# completed; a completed object is not selectable by this rule. Nothing here expires
# current or noncurrent object versions: no expiry rule is safe for this bucket, since
# an Upload row's bytes are expected to outlive any fixed window (takedown keeps them
# on purpose), so an expiry rule would silently delete live media.
#
# Deliberate consequence: noncurrent versions are unbounded. Acceptable — but NOT
# because they never appear. They do: every takedown and every restore deletes its
# source, leaving one behind (see the versioning block above). It is acceptable because
# those noncurrent versions ARE the recovery net. A noncurrent-version expiry rule would
# put a clock on exactly the bytes versioning is retained to save, silently converting a
# reversible takedown into a permanent one the moment the window passed. They accrue per
# moderation action only, never per upload or per read (file_overwrite = False, so the
# app never overwrites a key). Revisit only WITH a retention decision (대표·법무).
resource "aws_s3_bucket_lifecycle_configuration" "media" {
  count  = var.create_media_bucket ? 1 : 0
  bucket = aws_s3_bucket.media[0].id

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.media]
}

# TLS-only. Every request to this bucket is a SigV4-signed call from the app tier (the
# ECS task role) — the signature and, on presigned forms, the query string itself are
# credentials, so a plaintext request would put them on the wire. Denies every non-TLS
# request regardless of who makes it.
data "aws_iam_policy_document" "media_tls_only" {
  count = var.create_media_bucket ? 1 : 0

  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.media[0].arn, "${aws_s3_bucket.media[0].arn}/*"]

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "media" {
  count  = var.create_media_bucket ? 1 : 0
  bucket = aws_s3_bucket.media[0].id
  policy = data.aws_iam_policy_document.media_tls_only[0].json

  # A bucket policy with block_public_policy racing it is rejected; make the BPA land
  # first so the policy is evaluated against the final public-access posture.
  depends_on = [aws_s3_bucket_public_access_block.media]
}

# No CORS configuration, deliberately.
#
# Checked both directions before omitting it:
# - WRITES never touch the browser→S3 path. Uploads go to Django (apps/uploads/api.py
#   default_storage.save()), server-side, from the ECS task. There is no presigned
#   POST/PUT anywhere in server/ or web/ — grepped, zero hits outside vendored botocore.
# - READS never touch the browser→S3 path either. Media is proxied: the browser loads
#   a site-relative /media/... URL, Django's gated view checks takedown status and
#   streams the bytes from here (apps/uploads/media.py). The browser never learns this
#   bucket exists, so CORS — a browser-enforced protocol — has nothing to govern.
#
# A permissive CORS rule here would therefore add attack surface (it would let any
# origin's JS read media bytes off the bucket) while enabling no feature the app has.
# Add one ONLY when something actually needs a cross-origin fetch/XHR of media
# (browser-direct uploads, or canvas/WebGL reads), and scope it to the web origin then.
