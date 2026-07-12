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
- IAM execution role (image pull, logs, read the referenced secrets) + minimal task role.
- CloudWatch log groups + security groups.

## What it does NOT create (deliberately)
- **VPC/subnets** — supply an existing network via `vpc_id` / `*_subnet_ids`.
- **RDS / ElastiCache** — account-managed; pass connection strings as `container_secrets`
  (`DATABASE_URL`, `REDIS_URL`). Local dev uses compose pg16/redis7.
- **Secret material** — only secret **ARNs** are referenced (`container_secrets`); values
  live in Secrets Manager/SSM.
- **Object storage (S3) / CDN** — a documented backend gap, not yet wired anywhere.

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
| `ecs_cluster_name`            | `ASSEN_ECS_CLUSTER`            |
| `ecs_api_service_name`        | `ASSEN_ECS_API_SERVICE`        |
| `ecs_worker_service_name`     | `ASSEN_ECS_WORKER_SERVICE`     |
| `ecs_beat_service_name`       | `ASSEN_ECS_BEAT_SERVICE`       |
| `ecs_migrate_taskdef_family`  | `ASSEN_ECS_MIGRATE_TASKDEF`    |
| `alb_dns_name`                | DNS target for `ASSEN_PROD_API_URL` |

CI validates this stack via `.github/workflows/infra-ci.yml`.
