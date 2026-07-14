# ALB security group — accepts public HTTP/HTTPS.
resource "aws_security_group" "alb" {
  name        = "${local.name}-alb"
  description = "Public ingress to the ALB"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP (redirect to HTTPS at the listener)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All egress"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Service security group — API accepts traffic only from the ALB; all tasks egress
# freely (to RDS/ElastiCache/Secrets Manager/ECR, which live elsewhere in the VPC).
resource "aws_security_group" "service" {
  name        = "${local.name}-service"
  description = "ECS Fargate tasks"
  vpc_id      = var.vpc_id

  ingress {
    description     = "API port from the ALB only"
    from_port       = var.api_container_port
    to_port         = var.api_container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # Web port from the ALB when the same-origin web service is deployed. Kept INLINE
  # (not a separate aws_security_group_rule) — mixing the two makes each apply revoke
  # the other's rules, which silently drops the web target out of the ALB.
  dynamic "ingress" {
    for_each = var.deploy_web ? [1] : []
    content {
      description     = "Web port from the ALB (same-origin web service)"
      from_port       = var.web_container_port
      to_port         = var.web_container_port
      protocol        = "tcp"
      security_groups = [aws_security_group.alb.id]
    }
  }

  egress {
    description = "All egress"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
