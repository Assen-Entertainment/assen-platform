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

# Task role — the app's own runtime identity (what the CONTAINER's own AWS calls sign
# with), as opposed to the execution role above (what the ECS agent uses to pull the
# image and read secrets, never the app). Every grant the application code needs at
# runtime — media S3, SES — attaches HERE and nowhere else. Each is gated on its own
# config being present, so a role with nothing configured stays empty.
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

# Transactional email (SES) — config.email.SesEmailSender sends the signup verification
# mail with boto3 SESv2, signing with THIS role (the ambient task role). That is the
# whole reason the SES API was chosen over SES-over-SMTP: SMTP would need a static,
# long-lived IAM SMTP credential pair shipped in the environment, whereas the API needs
# only the grant below. Empty ses_identity_arn (default) = no policy, matching the
# environments where EMAIL_SENDER_BACKEND is unset and email_sender() returns None.
#
# Actions: ses:SendEmail ONLY. SESv2 send_email authorizes against ses:SendEmail for
# Simple/Templated content and additionally ses:SendRawEmail for Raw content — and the
# sender builds Content={"Simple": {...}} (a plain-text Korean body, no MIME assembly,
# no attachments), so ses:SendRawEmail is NOT required and is deliberately not granted.
# Add it only if the sender ever switches to Raw/MIME content (e.g. HTML + attachments).
#
# Scoping: ses:SendEmail's resource IS the identity ARN — the domain or address the mail
# is sent FROM. Scoping to var.ses_identity_arn therefore means this role can send only
# as the platform's own verified identity; it cannot send as any other identity that
# exists (now or later) in the same account. A "*" resource would silently grant that.
data "aws_iam_policy_document" "ses_send" {
  count = var.ses_identity_arn != "" ? 1 : 0

  statement {
    sid       = "SendVerificationEmail"
    actions   = ["ses:SendEmail"]
    resources = [var.ses_identity_arn]
  }
}

resource "aws_iam_role_policy" "task_ses_send" {
  count  = var.ses_identity_arn != "" ? 1 : 0
  name   = "${local.name}-ses-send"
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.ses_send[0].json
}
