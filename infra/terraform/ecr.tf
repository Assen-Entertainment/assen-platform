# The container image repositories. Created here by default; set
# create_ecr_repository=false to reference existing repos via image_repository_url /
# web_image_repository_url.
resource "aws_ecr_repository" "api" {
  count = var.create_ecr_repository ? 1 : 0

  name                 = "${var.name_prefix}-platform-api"
  image_tag_mutability = "MUTABLE" # the mutable prod tag is rolled per deploy

  image_scanning_configuration {
    scan_on_push = true
  }
}

# The web (Next.js) image repository — the web service is part of the release, so its
# image needs a home in the same registry (scripts/build-prod-image.sh builds and
# pushes it alongside the api image). Only created when the web service is deployed.
resource "aws_ecr_repository" "web" {
  count = var.create_ecr_repository && var.deploy_web ? 1 : 0

  name                 = "${var.name_prefix}-platform-web"
  image_tag_mutability = "MUTABLE" # the mutable prod tag is rolled per deploy

  image_scanning_configuration {
    scan_on_push = true
  }
}

# Lifecycle policy shared by both repositories.
#
# ECR has NO "retain" action — the only action is `expire`, so an image survives only
# by matching NO rule. The previous policy was a single `tagStatus: "any"` +
# `imageCountMoreThan: 20` rule, which selected *everything*: because these repos are
# account-global (one repo serves dev/staging/prod — see prod.tfvars), 20 dev pushes
# could expire the very image production runs, since main.tf pins the ECS task
# definitions to the mutable `:prod` tag. A dev deploy could delete the live prod image.
#
# The rule below therefore selects only images that NOTHING can reference. Everything
# tagged — above all the `:prod` image — is unselectable by any rule here, by design.
#
# ⚠️ Deliberate consequence: this does NOT bound storage for retired commit-SHA images,
# and no rule added here could, given the current tagging scheme. Every build tags its
# image `<commit-sha>` + `<env>` (build-prod-image.sh, deploy-dev.sh). When the mutable
# `:prod`/`:dev` tag moves to the next build, the retired image keeps its BARE HEX sha
# tag — so it stays "tagged" forever, while the live prod image ALSO carries a bare sha
# tag. ECR can only select tagged images by tag PREFIX, and a hex sha has no prefix that
# distinguishes a retired image from the live prod one. Any count-based rule wide enough
# to expire retired shas is therefore also wide enough to expire the live prod image —
# which is exactly the bug being fixed. An `imageCountMoreThan` rule on tagPrefixList
# ["dev"] would be worse than useless: only ONE image holds `:dev` at a time, so it can
# never fire, while reading as if storage were bounded.
#
# Bounding retired shas safely requires a TAGGING change, not a policy change: tag the
# immutable side per environment (`prod-<sha>` / `dev-<sha>`) instead of a bare `<sha>`.
# Each env then partitions cleanly, the live mutable tag is always the newest of its own
# partition (so `imageCountMoreThan` can never evict it), and both can be bounded. That
# changes the documented rollback/tag contract, so it is a deliberate follow-up, not a
# silent edit here. Until then ECR storage is ~$0.10/GB-month; prune retired shas by hand.
locals {
  ecr_lifecycle_policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after 14 days; never selects a tagged release image"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 14
        }
        action = { type = "expire" }
      }
    ]
  })
}

resource "aws_ecr_lifecycle_policy" "api" {
  count = var.create_ecr_repository ? 1 : 0

  repository = aws_ecr_repository.api[0].name
  policy     = local.ecr_lifecycle_policy
}

resource "aws_ecr_lifecycle_policy" "web" {
  count = var.create_ecr_repository && var.deploy_web ? 1 : 0

  repository = aws_ecr_repository.web[0].name
  policy     = local.ecr_lifecycle_policy
}
