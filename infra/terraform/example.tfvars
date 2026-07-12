# Copy to prod.tfvars (git-ignored) and fill with your account values, then
# `terraform plan/apply -var-file=prod.tfvars`. Nothing here is a real value.

aws_region  = "ap-northeast-2"
environment = "prod"

# --- Existing network (not provisioned by this stack) ---
vpc_id             = "vpc-xxxxxxxx"
public_subnet_ids  = ["subnet-aaaa", "subnet-bbbb"]
private_subnet_ids = ["subnet-cccc", "subnet-dddd"]

# --- Image ---
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
container_environment = {
  DJANGO_SETTINGS_MODULE = "config.settings.prod"
  # ALLOWED_HOSTS, DJANGO_ALLOWED_ORIGINS, etc.
}

# --- Secret ARNs (values live in Secrets Manager / SSM — only ARNs here) ---
container_secrets = {
  SECRET_KEY                 = "arn:aws:secretsmanager:ap-northeast-2:<acct>:secret:assen/secret-key"
  DATABASE_URL               = "arn:aws:secretsmanager:ap-northeast-2:<acct>:secret:assen/database-url"
  REDIS_URL                  = "arn:aws:secretsmanager:ap-northeast-2:<acct>:secret:assen/redis-url"
  PHONE_IDENTIFIER_HMAC_KEY  = "arn:aws:secretsmanager:ap-northeast-2:<acct>:secret:assen/phone-hmac-key"
}
