#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/lib/common.sh"

cd "$REPO_ROOT"

COMMIT_SHA="${COMMIT_SHA:-$(short_commit_sha)}"
IMAGE_REPOSITORY="${ASSEN_IMAGE_REPOSITORY:-${ASSEN_ECR_REPOSITORY_URI:-assen-platform-api}}"
PROD_IMAGE_TAG="${ASSEN_PROD_IMAGE_TAG:-prod-candidate}"

echo "prod image build: repository=${IMAGE_REPOSITORY} commit=${COMMIT_SHA} tag=${PROD_IMAGE_TAG}"
docker_run build \
  --pull \
  --build-arg "COMMIT_SHA=${COMMIT_SHA}" \
  -t "${IMAGE_REPOSITORY}:${COMMIT_SHA}" \
  -t "${IMAGE_REPOSITORY}:${PROD_IMAGE_TAG}" \
  server

echo "prod image build: done"
