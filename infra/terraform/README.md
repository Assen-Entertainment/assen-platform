# Assen platform — ECS Fargate IaC (terraform)

Infrastructure-as-Code for the production runtime: an ECS Fargate cluster running the
API, Celery worker, and Celery beat services, plus the one-off schema-migrate task —
the exact shape `scripts/deploy-prod-ecs.sh` deploys to. It provisions into an
**existing VPC** (network is an input, not authored here).

> ## ⚠️ STATUS: authored + CI-validated, **NOT YET APPLIED**
> Provisioning an AWS account/environment is the **E10 gate** (`docs/adr/0003-hosting-aws.md`,
> `docs/deployment.md`: "actual cloud runtime: not yet provisioned"). This stack is
> **config-validated in CI** (`terraform fmt -check` + `terraform validate`, no creds),
> but it has **never been `plan`/`apply`-ed against a live account**. Do not treat it as
> deployed. A real first apply will surface account-specific details (quotas, IAM
> boundaries, exact secret ARNs) that `validate` cannot.

## What it creates
- `aws_ecr_repository` — the api image repo (or reference an existing one).
- `aws_ecs_cluster` + task definitions (`api`, `worker`, `beat`, `migrate`) + services.
- ALB + target group + listener (health check `/healthz`).
- IAM execution role (image pull, logs, read the referenced secrets) + task role.
- **Media S3 bucket** (`create_media_bucket = true`) — private: block-all-public-access,
  ACLs disabled (`BucketOwnerEnforced`), SSE-S3, versioned, TLS-only, abort-incomplete-MPU.
- CloudWatch log groups + security groups.

### Two roles, and which grant goes where
- **Execution role** — the ECS *agent*'s identity: pull the image, write logs, read the
  `container_secrets` ARNs. The application never uses it.
- **Task role** — the *application*'s own runtime identity. Every AWS call the Django
  code makes signs with this: media S3 (`media_s3_bucket`) and SES (`ses_identity_arn`).
  Both grants are gated on their config being set, so an unconfigured env has an empty
  task role. This is why the app needs no static AWS keys anywhere.

## What it does NOT create (deliberately)
- **VPC/subnets** — supply an existing network via `vpc_id` / `*_subnet_ids`.
- **RDS / ElastiCache** — account-managed; pass connection strings as `container_secrets`
  (`DATABASE_URL`, `REDIS_URL`). Local dev uses compose pg16/redis7.
- **Secret material** — only secret **ARNs** are referenced (`container_secrets`); values
  live in Secrets Manager/SSM.
- **SES identity / DKIM / sandbox exit** — terraform only grants `ses:SendEmail` scoped to
  `ses_identity_arn`. *Verifying* the identity, publishing DKIM records, and leaving the
  SES sandbox are account/DNS actions done out-of-band (see the prod deploy runbook).
  The grant is useless until they are done, and `validate` cannot detect that.
- **CDN (CloudFront)** — media is served by signed S3 GET URLs directly; no CDN yet.

## Apply (once AWS is provisioned)
```sh
cd infra/terraform
terraform init \
  -backend-config="bucket=<tfstate-bucket>" \
  -backend-config="key=prod/ecs.tfstate" \
  -backend-config="region=ap-northeast-2" \
  -backend-config="dynamodb_table=<lock-table>"
terraform plan  -var-file=prod.tfvars    # prod.tfvars is git-ignored
terraform apply -var-file=prod.tfvars
```

## Wiring to the deploy script
The outputs map 1:1 to `scripts/deploy-prod-ecs.sh` env:

| terraform output              | deploy-prod-ecs.sh env         |
| ----------------------------- | ------------------------------ |
| `ecr_repository_url`          | `ASSEN_ECR_REPOSITORY_URI`     |
| `web_ecr_repository_url`      | `ASSEN_WEB_ECR_REPOSITORY_URI` |
| `ecs_cluster_name`            | `ASSEN_ECS_CLUSTER`            |
| `ecs_api_service_name`        | `ASSEN_ECS_API_SERVICE`        |
| `ecs_worker_service_name`     | `ASSEN_ECS_WORKER_SERVICE`     |
| `ecs_beat_service_name`       | `ASSEN_ECS_BEAT_SERVICE`       |
| `ecs_web_service_name`        | `ASSEN_ECS_WEB_SERVICE`        |
| `ecs_migrate_taskdef_family`  | `ASSEN_ECS_MIGRATE_TASKDEF`    |
| `alb_dns_name`                | DNS target for `ASSEN_PROD_API_URL` |
| `media_bucket_name`           | `DJANGO_MEDIA_S3_BUCKET` (in `container_environment`) |
| `media_bucket_arn`            | — (scope of the task role's S3 grant; reference only) |

The web values require `deploy_web = true` (the soft launch ships the web MVP, so the
prod stack sets it). `deploy-prod-ecs.sh` asserts both web vars and refuses to run
without them, so an api-only release cannot silently ship a stale frontend.

`media_bucket_name` is an output *and* an input: `media_s3_bucket` grants the task role
access, while `DJANGO_MEDIA_S3_BUCKET` in `container_environment` is what makes the app
route to S3 at all. They must name the same bucket — setting either alone is a half-wire
(a backend with no access → every upload 500s; access with no backend → still on local
disk). Uploads additionally need `ALLOW_UPLOADS = "True"`.

CI validates this stack via `.github/workflows/infra-ci.yml`.
