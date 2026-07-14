data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# Execution role — used by the ECS agent to pull the image, write logs, and read the
# secrets referenced by the task definitions (NOT the app's runtime role).
resource "aws_iam_role" "execution" {
  name               = "${local.name}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Allow the execution role to read exactly the secret ARNs the containers use.
data "aws_iam_policy_document" "secrets_read" {
  count = length(var.container_secrets) > 0 ? 1 : 0

  statement {
    actions   = ["secretsmanager:GetSecretValue", "ssm:GetParameters"]
    resources = values(var.container_secrets)
  }
}

resource "aws_iam_role_policy" "execution_secrets" {
  count = length(var.container_secrets) > 0 ? 1 : 0

  name   = "${local.name}-read-secrets"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.secrets_read[0].json
}

# Task role — the app's own runtime identity. Deliberately minimal (no S3/CDN yet —
# object storage is a documented backend gap). Extend when real integrations land.
resource "aws_iam_role" "task" {
  name               = "${local.name}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

# Media object storage (S3) — the app's runtime (task) role reads/writes the media
# bucket when one is configured (var.media_s3_bucket). Empty (default) = no S3 access,
# matching the local-filesystem media backend used by dev/demo. Scoped to this bucket.
data "aws_iam_policy_document" "media_s3" {
  count = var.media_s3_bucket != "" ? 1 : 0

  statement {
    sid       = "Objects"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["arn:aws:s3:::${var.media_s3_bucket}/*"]
  }

  statement {
    sid       = "ListBucket"
    actions   = ["s3:ListBucket"]
    resources = ["arn:aws:s3:::${var.media_s3_bucket}"]
  }
}

resource "aws_iam_role_policy" "task_media_s3" {
  count  = var.media_s3_bucket != "" ? 1 : 0
  name   = "${local.name}-media-s3"
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.media_s3[0].json
}
