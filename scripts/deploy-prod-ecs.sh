#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/lib/common.sh"

cd "$REPO_ROOT"

AWS_REGION="${AWS_REGION:-ap-northeast-2}"
COMMIT_SHA="${COMMIT_SHA:-$(short_commit_sha)}"
FULL_SHA="$(full_commit_sha)"
PROD_IMAGE_TAG="${ASSEN_PROD_IMAGE_TAG:-prod}"

if [ "${ASSEN_PROD_DEPLOY_APPROVED:-}" != "1" ]; then
  echo "error: set ASSEN_PROD_DEPLOY_APPROVED=1 after human production approval" >&2
  exit 1
fi

BRANCH="$(git branch --show-current)"
if [ "$BRANCH" != "main" ] && [ "${ASSEN_ALLOW_NON_MAIN_PROD_DEPLOY:-}" != "1" ]; then
  echo "error: production deploy must run from main; current branch is ${BRANCH}" >&2
  exit 1
fi

require_clean_worktree
require_cmd aws
require_cmd curl

: "${ASSEN_ECR_REPOSITORY_URI:?set ASSEN_ECR_REPOSITORY_URI}"
: "${ASSEN_ECS_CLUSTER:?set ASSEN_ECS_CLUSTER}"
: "${ASSEN_ECS_API_SERVICE:?set ASSEN_ECS_API_SERVICE}"
: "${ASSEN_ECS_WORKER_SERVICE:?set ASSEN_ECS_WORKER_SERVICE}"
: "${ASSEN_ECS_BEAT_SERVICE:?set ASSEN_ECS_BEAT_SERVICE}"
: "${ASSEN_PROD_API_URL:?set ASSEN_PROD_API_URL}"

if [ "${ASSEN_SKIP_GITHUB_CI_CHECK:-}" != "1" ]; then
  require_cmd gh
  CI_STATE="$(
    gh run list \
      --repo Assen-Entertainment/assen-platform \
      --workflow CI \
      --commit "$FULL_SHA" \
      --limit 1 \
      --json status,conclusion \
      --jq '.[0] | "\(.status) \(.conclusion)"'
  )"
  if [ "$CI_STATE" != "completed success" ]; then
    echo "error: latest CI for ${FULL_SHA} is not completed success: ${CI_STATE}" >&2
    exit 1
  fi
fi

REGISTRY_HOST="$(printf '%s' "$ASSEN_ECR_REPOSITORY_URI" | awk -F/ '{print $1}')"

echo "prod deploy: logging into ECR ${REGISTRY_HOST}"
aws ecr get-login-password --region "$AWS_REGION" |
  "$(docker_cmd)" login --username AWS --password-stdin "$REGISTRY_HOST"

echo "prod deploy: building image"
ASSEN_IMAGE_REPOSITORY="$ASSEN_ECR_REPOSITORY_URI" \
ASSEN_PROD_IMAGE_TAG="$PROD_IMAGE_TAG" \
COMMIT_SHA="$COMMIT_SHA" \
  "$SCRIPT_DIR/build-prod-image.sh"

echo "prod deploy: pushing image tags"
docker_run push "${ASSEN_ECR_REPOSITORY_URI}:${COMMIT_SHA}"
docker_run push "${ASSEN_ECR_REPOSITORY_URI}:${PROD_IMAGE_TAG}"

echo "prod deploy: forcing ECS deployments"
for SERVICE in "$ASSEN_ECS_API_SERVICE" "$ASSEN_ECS_WORKER_SERVICE" "$ASSEN_ECS_BEAT_SERVICE"; do
  aws ecs update-service \
    --region "$AWS_REGION" \
    --cluster "$ASSEN_ECS_CLUSTER" \
    --service "$SERVICE" \
    --force-new-deployment \
    >/dev/null
done

echo "prod deploy: waiting for ECS services to stabilize"
aws ecs wait services-stable \
  --region "$AWS_REGION" \
  --cluster "$ASSEN_ECS_CLUSTER" \
  --services "$ASSEN_ECS_API_SERVICE" "$ASSEN_ECS_WORKER_SERVICE" "$ASSEN_ECS_BEAT_SERVICE"

echo "prod deploy: smoke /healthz"
curl -fsS "${ASSEN_PROD_API_URL%/}/healthz"
printf '\n'

echo "prod deploy: smoke /api/health"
curl -fsS "${ASSEN_PROD_API_URL%/}/api/health"
printf '\n'

cat <<EOF
prod deploy: complete
- commit: ${FULL_SHA}
- image: ${ASSEN_ECR_REPOSITORY_URI}:${COMMIT_SHA}
- mutable tag: ${ASSEN_ECR_REPOSITORY_URI}:${PROD_IMAGE_TAG}
- cluster: ${ASSEN_ECS_CLUSTER}
- services: ${ASSEN_ECS_API_SERVICE}, ${ASSEN_ECS_WORKER_SERVICE}, ${ASSEN_ECS_BEAT_SERVICE}
- smoke: ${ASSEN_PROD_API_URL%/}/api/health
EOF
