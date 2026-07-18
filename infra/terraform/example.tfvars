# Copy to prod.tfvars (git-ignored) and fill with your account values, then
# `terraform plan/apply -var-file=prod.tfvars`. Nothing here is a real value.
#
# Every env-var NAME below is verified against server/config/settings/prod.py and
# base.py — do not rename them. prod.py reads the security-critical values through a
# schema-less Env, so a missing/misnamed key does not fall back to a default: the
# container fails to boot. (That is why this file previously being wrong was harmful:
# it named SECRET_KEY and REDIS_URL, neither of which prod.py reads.)

aws_region  = "ap-northeast-2"
environment = "prod"

# --- Existing network (not provisioned by this stack) ---
vpc_id             = "vpc-xxxxxxxx"
public_subnet_ids  = ["subnet-aaaa", "subnet-bbbb"]
private_subnet_ids = ["subnet-cccc", "subnet-dddd"]

# --- Image ---
# true = this stack creates the api repo (and the web repo when deploy_web = true).
# Set false and pass image_repository_url / web_image_repository_url if the repos
# already exist in the account (they are account-global, not per-environment).
create_ecr_repository = true
image_tag             = "prod"

# --- Scaling / size ---
api_desired_count    = 2
worker_desired_count = 1
beat_desired_count   = 1
task_cpu             = 512
task_memory          = 1024

# --- TLS (ALB HTTPS listener) ---
acm_certificate_arn = "arn:aws:acm:ap-northeast-2:<acct>:certificate/xxxx"

# --- Non-secret container env ---
# Anything prod.py hard-requires at boot is listed; nothing here is a secret.
container_environment = {
  DJANGO_SETTINGS_MODULE = "config.settings.prod"

  # prod.py:27 — comma-separated (env.list). Never "*" in production.
  DJANGO_ALLOWED_HOSTS = "api.example.com"

  # prod.py:92 — web origin(s) allowed to POST with CSRF; scheme included.
  DJANGO_CSRF_TRUSTED_ORIGINS = "https://example.com"

  # prod.py:39-40 — required; the worker/beat services genuinely use these.
  CELERY_BROKER_URL     = "redis://redis.internal:6379/0"
  CELERY_RESULT_BACKEND = "redis://redis.internal:6379/0"

  # prod.py:56-69 — the shared limiter is mandatory in prod: RATELIMIT_BACKEND must
  # be exactly "redis", RATELIMIT_REDIS_URL must be non-empty, and TRUSTED_PROXY_HOPS
  # must be >= 1 behind the ALB. Any of these wrong = ImproperlyConfigured at boot.
  RATELIMIT_BACKEND   = "redis"
  RATELIMIT_REDIS_URL = "redis://redis.internal:6379/1"
  TRUSTED_PROXY_HOPS  = "1"

  # --- Transactional email (base.py:67-74) ---
  # "" | "mock" | "ses" | "smtp". config.email.email_sender() is fail-closed: a backend
  # that is unset OR only partially configured yields None and the signup surface 503s
  # (never a sender that raises on every signup). "ses" needs ALL THREE of
  # EMAIL_SES_REGION / EMAIL_FROM_ADDRESS / WEB_BASE_URL, plus var.ses_identity_arn
  # below so the task role may actually send.
  EMAIL_SENDER_BACKEND = "ses"

  # From: address of the verification mail. MUST belong to the SES verified identity in
  # ses_identity_arn — SES rejects a send from an unverified address, and the IAM policy
  # is scoped to that identity, so a mismatch fails twice over.
  EMAIL_FROM_ADDRESS = "no-reply@example.com"

  # SES region. Only the region is configured — boto3 signs with the ambient task role,
  # so there are NO static SES keys to place here or in container_secrets, by design.
  # SES is regional: the identity must be verified in THIS region.
  EMAIL_SES_REGION = "ap-northeast-2"

  # Origin of the WEB app the verify link points at ({WEB_BASE_URL}/verify-email?token=…).
  # The fan lands on a web page, so this is the web origin, NOT the API host.
  WEB_BASE_URL = "https://example.com"

  # --- Uploads (base.py:450) ---
  # The ONLY switch on the upload surface (apps.uploads.api 503s +
  # UPLOAD_STORAGE_UNAVAILABLE when off). Env-driven, default False = fail-closed.
  # Necessary but not sufficient: apps.uploads.api also requires that the STORE can
  # hold the object (config.storage.media_storage_ready — in practice, that an
  # object-storage backend names a bucket), so ALLOW_UPLOADS ON with no object store
  # still 503s, by design. ON + the S3 bucket below = the correct production posture.
  #
  # There is no second flag: media is served by Django's gated view on EVERY backend
  # (apps.uploads.media), so "can anything serve this?" is no longer a variable. The
  # old SERVE_LOCAL_MEDIA flag was retired for exactly that reason (base.py:446-449) —
  # do not set it anywhere; nothing reads it.
  ALLOW_UPLOADS = "True"

  # --- Media object storage (base.py:501-526) ---
  # Setting this routes STORAGES["default"] to a PRIVATE S3 bucket. Reads do NOT go to
  # the bucket: Django serves every media byte through its gated view (apps.uploads.media),
  # so the bucket stays private with the app tier as its only reader, the served URL never
  # expires, and a moderation takedown is immediate.
  # MUST equal var.media_s3_bucket below — that variable only grants the task role
  # access to the bucket; THIS env var is what makes the app actually use it. Setting
  # one without the other is the classic half-wire (access with no backend → uploads
  # silently land on container-local disk, or a backend with no access → every upload
  # 500s on AccessDenied).
  DJANGO_MEDIA_S3_BUCKET = "assen-prod-media-<acct>"
  DJANGO_MEDIA_S3_REGION = "ap-northeast-2"
}

# --- Secret ARNs (values live in Secrets Manager / SSM — only ARNs here) ---
# Keys become the container env var names, so they must match prod.py exactly.
container_secrets = {
  # prod.py:26 — DJANGO_SECRET_KEY, *not* SECRET_KEY.
  DJANGO_SECRET_KEY = "arn:aws:secretsmanager:ap-northeast-2:<acct>:secret:assen/django-secret-key"

  # prod.py:38 — read with env.db(); postgres://USER:PASS@HOST:5432/DBNAME.
  DATABASE_URL = "arn:aws:secretsmanager:ap-northeast-2:<acct>:secret:assen/database-url"

  # prod.py:45-47 — distinct from the secret key; rejected at boot if < 32 bytes.
  PHONE_IDENTIFIER_HMAC_KEY = "arn:aws:secretsmanager:ap-northeast-2:<acct>:secret:assen/phone-hmac-key"

  # NOTE: there is deliberately no REDIS_URL here — no settings module reads it.
  # Redis is configured per use via CELERY_* / RATELIMIT_REDIS_URL above.
}

# --- Web (Next.js) service — same-origin with the API behind the same ALB ---
# scripts/build-prod-image.sh builds+pushes the web image and deploy-prod-ecs.sh rolls
# the web service, so the web repo/service must exist for a release to be complete.
deploy_web           = true
web_image_tag        = "prod"
web_desired_count    = 1
web_api_internal_url = "https://api.example.com/api" # SSR fetch base (absolute)

# --- Media object storage (S3) ---
# media_s3_bucket NAMES the bucket and grants the ECS *task* role scoped access to it
# (iam.tf: Get/Put/Delete on the objects, ListBucket on the bucket). It does NOT enable
# the backend — DJANGO_MEDIA_S3_BUCKET in container_environment does, and the two must
# name the same bucket.
media_s3_bucket = "assen-prod-media-<acct>"

# Whether THIS stack creates that bucket (media.tf: block-all-public-access, ACLs
# disabled, SSE-S3, versioned, TLS-only). Create-or-reference, exactly like
# create_ecr_repository. false (default) = the bucket already exists in the account and
# is only referenced — which is what dev/staging do, so their applies create nothing.
# Set true for a greenfield prod bucket; leave false if it was made out-of-band.
create_media_bucket = true

# --- Transactional email (SES) ---
# ARN of the SES VERIFIED identity the app sends from. The task role's ses:SendEmail is
# scoped to exactly this identity, so the role can send only as the platform's own
# domain/address — never as some other identity in the account. Empty (default) = no SES
# policy at all. Identity verification (+ DKIM, + production-access/sandbox exit) is an
# account action, NOT terraform — see the prod deploy runbook.
# Domain identity:  arn:aws:ses:ap-northeast-2:<acct>:identity/example.com
# Address identity: arn:aws:ses:ap-northeast-2:<acct>:identity/no-reply@example.com
ses_identity_arn = "arn:aws:ses:ap-northeast-2:<acct>:identity/example.com"
