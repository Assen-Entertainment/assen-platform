# Deployment and Local Build

This document records the current deployment status and the repeatable scripts
for local/dev builds and production deployment preparation.

## Current Status

As of 2026-06-12:

- Source repository: `https://github.com/Assen-Entertainment/assen-platform`
  (private).
- Default branch on GitHub: `dev`.
- GitOps branch contract in `AGENTS.md`: `dev` is the integration/dev deploy
  source, `main` is production desired state.
- GitHub Deployments API: no deployment records.
- GitHub Environments API: no environments configured.
- Latest verified remote state: CI on `dev` commit
  `f4e167c6dc4f0767d3160a0c5886b22b4467eabe` completed successfully.
- Target hosting architecture: AWS Seoul (`ap-northeast-2`) + ECS Fargate per
  `docs/adr/0003-hosting-aws.md`.
- Actual cloud dev/prod runtime: not yet provisioned in this repository.

Local runtime can be started with Docker Compose. It runs:

- PostgreSQL 16 on `127.0.0.1:5432`
- Redis 7 on `127.0.0.1:6379`
- Django API on `http://127.0.0.1:8000`
- Celery worker
- Celery beat

## Local / Dev Build

Build local artifacts and backend images:

```sh
scripts/build-local.sh
```

Useful overrides:

```sh
BUILD_ANDROID_DEBUG=0 scripts/build-local.sh
FLUTTER_APP=operator_app BUILD_BACKEND_IMAGE=0 scripts/build-local.sh
```

Start the local backend stack, apply local migrations, and run smoke checks:

```sh
scripts/up-local.sh
```

Smoke an already running local stack:

```sh
scripts/smoke-local.sh
```

These scripts set `COMMIT_SHA` from the current git commit unless the caller
already provided it, so `/api/health` can report which image is running.

## Local Web Shell

Build the composed local web shell:

```sh
scripts/build-web-local.sh
```

Serve it on localhost:

```sh
scripts/serve-web-local.sh
```

Then open `http://127.0.0.1:8080`. The landing page is served at `/`, and the
Flutter fan app is served at `/app/`. Use `WEB_PORT=8081` to serve on another
port.

## Production Image Build

Build the backend container image without deploying:

```sh
ASSEN_IMAGE_REPOSITORY=assen-platform-api scripts/build-prod-image.sh
```

For ECR:

```sh
ASSEN_ECR_REPOSITORY_URI=<aws-account>.dkr.ecr.ap-northeast-2.amazonaws.com/assen-platform-api \
scripts/build-prod-image.sh
```

The image is tagged with both:

- `${COMMIT_SHA}`
- `${ASSEN_PROD_IMAGE_TAG:-prod-candidate}`

## Production ECS Deploy

Production deployment is human-gated. The script refuses to run unless:

- `ASSEN_PROD_DEPLOY_APPROVED=1` is set after human approval.
- The current branch is `main`, unless `ASSEN_ALLOW_NON_MAIN_PROD_DEPLOY=1`.
- The tracked worktree is clean.
- The latest GitHub CI run for the commit is `completed success`, unless
  `ASSEN_SKIP_GITHUB_CI_CHECK=1`.

Required environment:

```sh
AWS_REGION=ap-northeast-2
ASSEN_PROD_DEPLOY_APPROVED=1
ASSEN_ECR_REPOSITORY_URI=<aws-account>.dkr.ecr.ap-northeast-2.amazonaws.com/assen-platform-api
ASSEN_ECS_CLUSTER=<ecs-cluster-name>
ASSEN_ECS_API_SERVICE=<api-service-name>
ASSEN_ECS_WORKER_SERVICE=<celery-worker-service-name>
ASSEN_ECS_BEAT_SERVICE=<celery-beat-service-name>
ASSEN_PROD_API_URL=https://<production-api-host>
```

Run:

```sh
scripts/deploy-prod-ecs.sh
```

The script builds and pushes `${COMMIT_SHA}` and `prod` image tags, then forces
a new deployment for the API, Celery worker, and Celery beat ECS services. ECS
task definitions must be configured to use the mutable production tag
`${ASSEN_PROD_IMAGE_TAG:-prod}` for this script to roll the services forward.

The deploy is not complete until the script also passes:

- ECS `services-stable`
- `GET /healthz`
- `GET /api/health`

## Rollback

Rollback remains a GitOps operation:

- Re-run the deploy script with a previously verified image tag, or
- revert through Git and deploy the reverted `main`, or
- turn off the relevant feature flag where applicable.

Do not make unrecorded production console changes.
