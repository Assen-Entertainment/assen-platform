#!/usr/bin/env sh
# Deploy a non-prod Assen environment (default: dev): build+push the api and web
# images, run the one-off schema migrate, roll the ECS services, and smoke the ALB.
#
# Intentionally lighter than scripts/deploy-prod-ecs.sh — NO prod approval /
# main-branch / CI-green gates. This is the dev QA redeploy loop: run it after a
# code change to put the current checkout on the dev stack.
#
# Prereqs: aws + docker + a built dev stack (terraform apply -var-file=dev.tfvars),
# AWS creds with deploy permissions, region ap-northeast-2.
#
# Usage: scripts/deploy-dev.sh [env]        # env defaults to "dev"
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/lib/common.sh"
cd "$REPO_ROOT"

ENV="${1:-dev}"
AWS_REGION="${AWS_REGION:-ap-northeast-2}"
NAME="assen-${ENV}"
COMMIT_SHA="${COMMIT_SHA:-$(short_commit_sha)}"

require_cmd aws
require_cmd curl
DOCKER="$(docker_cmd)"

ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
REGISTRY="${ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"
API_REPO="${REGISTRY}/assen-platform-api"
WEB_REPO="${REGISTRY}/assen-platform-web"

CLUSTER="$NAME"
API_SVC="${NAME}-api"
WORKER_SVC="${NAME}-worker"
BEAT_SVC="${NAME}-beat"
WEB_SVC="${NAME}-web"
MIGRATE_TASKDEF="${NAME}-migrate"

echo "deploy-dev: env=${ENV} commit=${COMMIT_SHA} region=${AWS_REGION}"

# ALB DNS — the web's public origin (baked into NEXT_PUBLIC_SITE_URL) and smoke host.
ALB_DNS="$(aws elbv2 describe-load-balancers --names "${NAME}-api" \
  --region "$AWS_REGION" --query 'LoadBalancers[0].DNSName' --output text)"
SITE_URL="http://${ALB_DNS}"
echo "deploy-dev: alb=${ALB_DNS}"

echo "deploy-dev: ECR login"
aws ecr get-login-password --region "$AWS_REGION" \
  | "$DOCKER" login --username AWS --password-stdin "$REGISTRY"

echo "deploy-dev: build+push api image"
"$DOCKER" build --pull --build-arg "COMMIT_SHA=${COMMIT_SHA}" \
  -t "${API_REPO}:${COMMIT_SHA}" -t "${API_REPO}:${ENV}" server
"$DOCKER" push "${API_REPO}:${COMMIT_SHA}"
"$DOCKER" push "${API_REPO}:${ENV}"

# NEXT_PUBLIC_API_URL=/api is a RELATIVE path — the browser hits the same origin and
# the ALB routes /api/* to the API service (same-origin, no CORS/mixed-content).
echo "deploy-dev: build+push web image"
"$DOCKER" build \
  --build-arg "NEXT_PUBLIC_API_URL=/api" \
  --build-arg "NEXT_PUBLIC_SITE_URL=${SITE_URL}" \
  -t "${WEB_REPO}:${COMMIT_SHA}" -t "${WEB_REPO}:${ENV}" web
"$DOCKER" push "${WEB_REPO}:${COMMIT_SHA}"
"$DOCKER" push "${WEB_REPO}:${ENV}"

# Reuse the api service's network config for the one-off migrate task.
NC='services[0].networkConfiguration.awsvpcConfiguration'
SUBNET_CSV="$(aws ecs describe-services --cluster "$CLUSTER" --services "$API_SVC" \
  --region "$AWS_REGION" --query "${NC}.subnets" --output text | tr '\t' ',')"
SG_CSV="$(aws ecs describe-services --cluster "$CLUSTER" --services "$API_SVC" \
  --region "$AWS_REGION" --query "${NC}.securityGroups" --output text | tr '\t' ',')"
PUBIP="$(aws ecs describe-services --cluster "$CLUSTER" --services "$API_SVC" \
  --region "$AWS_REGION" --query "${NC}.assignPublicIp" --output text)"
NET="awsvpcConfiguration={subnets=[${SUBNET_CSV}],securityGroups=[${SG_CSV}],assignPublicIp=${PUBIP}}"

echo "deploy-dev: run schema migrate task"
MIGRATE_ARN="$(aws ecs run-task --cluster "$CLUSTER" --task-definition "$MIGRATE_TASKDEF" \
  --launch-type FARGATE --network-configuration "$NET" \
  --region "$AWS_REGION" --query 'tasks[0].taskArn' --output text)"
if [ -z "$MIGRATE_ARN" ] || [ "$MIGRATE_ARN" = "None" ]; then
  echo "error: migrate task was not placed (inspect ecs run-task failures)" >&2
  exit 1
fi
aws ecs wait tasks-stopped --cluster "$CLUSTER" --tasks "$MIGRATE_ARN" --region "$AWS_REGION"
MIGRATE_CODE="$(aws ecs describe-tasks --cluster "$CLUSTER" --tasks "$MIGRATE_ARN" \
  --region "$AWS_REGION" --query 'tasks[0].containers[0].exitCode' --output text)"
if [ "$MIGRATE_CODE" != "0" ]; then
  echo "error: migrate task exited with code ${MIGRATE_CODE} — aborting deploy" >&2
  exit 1
fi
echo "deploy-dev: migrate ok"

echo "deploy-dev: rolling services"
for SVC in "$API_SVC" "$WORKER_SVC" "$BEAT_SVC" "$WEB_SVC"; do
  aws ecs update-service --cluster "$CLUSTER" --service "$SVC" \
    --force-new-deployment --region "$AWS_REGION" >/dev/null
done

echo "deploy-dev: waiting for services to stabilize"
aws ecs wait services-stable --cluster "$CLUSTER" \
  --services "$API_SVC" "$WORKER_SVC" "$BEAT_SVC" "$WEB_SVC" --region "$AWS_REGION"

echo "deploy-dev: smoke"
curl -fsS "${SITE_URL}/healthz" >/dev/null && echo "  /healthz ok"
printf '  /api/health -> '; curl -fsS "${SITE_URL}/api/health"; printf '\n'
curl -fsS -o /dev/null -w "  / -> %{http_code}\n" "${SITE_URL}/"

echo "deploy-dev: complete (${ENV} @ ${COMMIT_SHA}) -> ${SITE_URL}"
