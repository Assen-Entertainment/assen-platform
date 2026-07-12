terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state. Configure per-account at `terraform init` time, e.g.:
  #   terraform init -backend-config="bucket=assen-tfstate" \
  #     -backend-config="key=prod/ecs.tfstate" \
  #     -backend-config="region=ap-northeast-2" \
  #     -backend-config="dynamodb_table=assen-tf-lock"
  # Left partial (no values) so CI can `terraform init -backend=false` to validate
  # without any AWS credentials or a real state bucket.
  backend "s3" {}
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "assen-platform"
      ManagedBy = "terraform"
      Env       = var.environment
    }
  }
}
