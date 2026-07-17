data "aws_region" "current" {}

data "aws_caller_identity" "current" {}

locals {
  name = "${var.name_prefix}-${var.environment}"

  # The api image the ECS task definitions reference. Either the repository created
  # here or an existing one supplied via image_repository_url, at the mutable tag the
  # deploy script rolls (scripts/deploy-prod-ecs.sh force-new-deployment).
  image_repository_url = var.create_ecr_repository ? aws_ecr_repository.api[0].repository_url : var.image_repository_url
  image                = "${local.image_repository_url}:${var.image_tag}"

  # Same rule for the web image (web.tf): the repo created here when the web service
  # is deployed, else the existing one supplied via web_image_repository_url.
  web_image_repository_url = var.create_ecr_repository && var.deploy_web ? one(aws_ecr_repository.web[*].repository_url) : var.web_image_repository_url

  # ECS container "secrets" block: [{ name, valueFrom }] from the ARN map.
  container_secrets = [for k, v in var.container_secrets : { name = k, valueFrom = v }]

  # ECS container "environment" block: [{ name, value }] from the plain env map.
  container_environment = [for k, v in var.container_environment : { name = k, value = v }]
}
