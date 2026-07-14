# All account- and environment-specific values are variables — nothing account
# specific is hardcoded. Provide them via a *.tfvars file (git-ignored) or -var flags.

variable "aws_region" {
  description = "AWS region for the ECS deployment (hosting = AWS Seoul, ADR-0003)."
  type        = string
  default     = "ap-northeast-2"
}

variable "environment" {
  description = "Deployment environment name (prod, staging)."
  type        = string
  default     = "prod"
}

variable "name_prefix" {
  description = "Prefix for all resource names."
  type        = string
  default     = "assen"
}

# --- Networking (deploy into an EXISTING VPC — not provisioned here) ----------
variable "vpc_id" {
  description = "Existing VPC id to deploy into."
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet ids for the internet-facing ALB (>= 2 AZs)."
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "Private subnet ids for the Fargate tasks (>= 2 AZs)."
  type        = list(string)
}

variable "assign_public_ip" {
  description = "Assign public IPs to the Fargate tasks. false (default) = private subnets behind NAT (production). true = a NAT-less deploy where the tasks sit on public subnets and reach ECR/Secrets/internet via the IGW directly (free-tier staging on the default VPC)."
  type        = bool
  default     = false
}

# --- Image ---------------------------------------------------------------------
variable "create_ecr_repository" {
  description = "Create the api ECR repository here (false = reference an existing one via image_repository_url)."
  type        = bool
  default     = true
}

variable "image_repository_url" {
  description = "ECR repository URL for the api image when create_ecr_repository=false (e.g. <acct>.dkr.ecr.ap-northeast-2.amazonaws.com/assen-platform-api)."
  type        = string
  default     = ""
}

variable "image_tag" {
  description = "Mutable image tag the ECS services track (deploy-prod-ecs.sh rolls this)."
  type        = string
  default     = "prod"
}

# --- Container runtime ---------------------------------------------------------
variable "api_container_port" {
  description = "Port the Django/gunicorn API listens on inside the container."
  type        = number
  default     = 8000
}

variable "api_desired_count" {
  description = "Desired number of API service tasks."
  type        = number
  default     = 2
}

variable "worker_desired_count" {
  description = "Desired number of celery worker tasks."
  type        = number
  default     = 1
}

variable "beat_desired_count" {
  description = "Desired number of celery beat tasks (must be exactly 1 — beat is a singleton scheduler)."
  type        = number
  default     = 1

  validation {
    condition     = var.beat_desired_count == 1
    error_message = "celery beat is a singleton scheduler; beat_desired_count must be 1."
  }
}

variable "task_cpu" {
  description = "Fargate task CPU units (256/512/1024/...)."
  type        = number
  default     = 512
}

variable "task_memory" {
  description = "Fargate task memory (MiB)."
  type        = number
  default     = 1024
}

# --- App configuration + secrets ----------------------------------------------
# Plain (non-secret) environment passed to every container.
variable "container_environment" {
  description = "Non-secret environment variables for the containers (e.g. DJANGO_SETTINGS_MODULE=config.settings.prod, ALLOWED_HOSTS)."
  type        = map(string)
  default     = {}
}

# Secret ARNs (Secrets Manager or SSM SecureString) injected as container secrets.
# The values live in the account — terraform only references the ARNs, never the
# secret material. Keys become the container env var names.
variable "container_secrets" {
  description = "Map of env-var-name => Secrets Manager/SSM ARN injected as ECS container secrets (e.g. SECRET_KEY, DATABASE_URL, REDIS_URL, PHONE_IDENTIFIER_HMAC_KEY)."
  type        = map(string)
  default     = {}
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for the ALB HTTPS listener. Empty = HTTP-only listener (not for production)."
  type        = string
  default     = ""
}

variable "log_retention_days" {
  description = "CloudWatch log retention (days)."
  type        = number
  default     = 30
}

# --- Web (Next.js) service — optional same-origin frontend on the same ALB ------
variable "deploy_web" {
  description = "Deploy the Next.js web app as a second ECS service behind the same ALB (same-origin). Default action → web; /api/*, /healthz, /readyz stay on the API. false = API-only stack (unchanged)."
  type        = bool
  default     = false
}

variable "web_image_repository_url" {
  description = "ECR repository URL for the web image (required when deploy_web=true)."
  type        = string
  default     = ""
}

variable "web_image_tag" {
  description = "Mutable web image tag the web service tracks."
  type        = string
  default     = "dev"
}

variable "web_container_port" {
  description = "Port the Next.js standalone server listens on."
  type        = number
  default     = 3000
}

variable "web_desired_count" {
  description = "Desired number of web service tasks."
  type        = number
  default     = 1
}

variable "web_task_cpu" {
  description = "Fargate CPU units for the web task."
  type        = number
  default     = 256
}

variable "web_task_memory" {
  description = "Fargate memory (MiB) for the web task."
  type        = number
  default     = 512
}

variable "web_api_internal_url" {
  description = "Absolute API base URL the web server uses for SSR fetches (API_INTERNAL_URL), e.g. http://<alb-dns>/api."
  type        = string
  default     = ""
}

variable "web_container_environment" {
  description = "Extra non-secret env for the web container."
  type        = map(string)
  default     = {}
}
