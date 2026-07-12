# The api container image repository. Created here by default; set
# create_ecr_repository=false to reference an existing repo via image_repository_url.
resource "aws_ecr_repository" "api" {
  count = var.create_ecr_repository ? 1 : 0

  name                 = "${var.name_prefix}-platform-api"
  image_tag_mutability = "MUTABLE" # the mutable prod tag is rolled per deploy

  image_scanning_configuration {
    scan_on_push = true
  }
}

# Keep only the most recent images; expire old commit-SHA tags to bound storage.
resource "aws_ecr_lifecycle_policy" "api" {
  count = var.create_ecr_repository ? 1 : 0

  repository = aws_ecr_repository.api[0].name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 20 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 20
        }
        action = { type = "expire" }
      }
    ]
  })
}
