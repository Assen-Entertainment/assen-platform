#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/lib/common.sh"

cd "$REPO_ROOT"

COMMIT_SHA="${COMMIT_SHA:-$(short_commit_sha)}"
IMAGE_REPOSITORY="${ASSEN_IMAGE_REPOSITORY:-${ASSEN_ECR_REPOSITORY_URI:-assen-platform-api}}"
WEB_IMAGE_REPOSITORY="${ASSEN_WEB_IMAGE_REPOSITORY:-${ASSEN_WEB_ECR_REPOSITORY_URI:-assen-platform-web}}"
PROD_IMAGE_TAG="${ASSEN_PROD_IMAGE_TAG:-prod-candidate}"

# The web bundle inlines NEXT_PUBLIC_* at BUILD time, so the public origin must be
# known here — it cannot be fixed later with runtime env. Fail closed rather than
# bake web/Dockerfile's http://localhost:3000 default into a production image.
# deploy-prod-ecs.sh passes this (defaulted to the same-origin ASSEN_PROD_API_URL).
: "${ASSEN_PROD_SITE_URL:?set ASSEN_PROD_SITE_URL (public web origin, e.g. https://assen.example)}"

echo "prod image build: repository=${IMAGE_REPOSITORY} commit=${COMMIT_SHA} tag=${PROD_IMAGE_TAG}"
docker_run build \
  --pull \
  --build-arg "COMMIT_SHA=${COMMIT_SHA}" \
  -t "${IMAGE_REPOSITORY}:${COMMIT_SHA}" \
  -t "${IMAGE_REPOSITORY}:${PROD_IMAGE_TAG}" \
  server

# The web image is part of the release, not a manual side-quest (mirrors
# scripts/deploy-dev.sh). NEXT_PUBLIC_API_URL=/api is a RELATIVE path: the browser
# hits the same origin and the ALB routes /api/* to the API service (web.tf's
# listener rule), so there is no CORS/mixed-content and no per-env API host baked in.
echo "prod image build: web repository=${WEB_IMAGE_REPOSITORY} site=${ASSEN_PROD_SITE_URL}"
docker_run build \
  --pull \
  --build-arg "NEXT_PUBLIC_API_URL=/api" \
  --build-arg "NEXT_PUBLIC_SITE_URL=${ASSEN_PROD_SITE_URL}" \
  -t "${WEB_IMAGE_REPOSITORY}:${COMMIT_SHA}" \
  -t "${WEB_IMAGE_REPOSITORY}:${PROD_IMAGE_TAG}" \
  web

echo "prod image build: done"
