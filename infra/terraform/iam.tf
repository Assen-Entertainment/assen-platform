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
