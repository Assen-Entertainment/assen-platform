# Optional Next.js web service — same-origin with the API behind the single ALB.
# Gated by var.deploy_web so the API-only stack (prod → Amplify path) is unaffected:
# when enabled, the listener default action forwards to the web target group (set in
# alb.tf) and the rule below keeps the API paths on the API service. Same origin →
# no CORS, no mixed-content. The web reaches the API for SSR via web_api_internal_url.

resource "aws_cloudwatch_log_group" "web" {
  count             = var.deploy_web ? 1 : 0
  name              = "/ecs/${local.name}/web"
  retention_in_days = var.log_retention_days
}

resource "aws_ecs_task_definition" "web" {
  count                    = var.deploy_web ? 1 : 0
  family                   = "${local.name}-web"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.web_task_cpu
  memory                   = var.web_task_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "web"
    image     = "${var.web_image_repository_url}:${var.web_image_tag}"
    essential = true
    environment = concat(
      [{ name = "API_INTERNAL_URL", value = var.web_api_internal_url }],
      [for k, v in var.web_container_environment : { name = k, value = v }],
    )
    portMappings = [{
      containerPort = var.web_container_port
      protocol      = "tcp"
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.web[0].name
        "awslogs-region"        = local.log_region
        "awslogs-stream-prefix" = "web"
      }
    }
  }])
}

resource "aws_lb_target_group" "web" {
  count       = var.deploy_web ? 1 : 0
  name        = "${local.name}-web"
  port        = var.web_container_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    path                = "/login"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

# The web tasks accept the web port from the ALB (the shared service SG only opened
# the API port). Added as a rule so the inline service-SG block in security.tf is left
# intact for the API-only case.
resource "aws_security_group_rule" "web_from_alb" {
  count                    = var.deploy_web ? 1 : 0
  type                     = "ingress"
  from_port                = var.web_container_port
  to_port                  = var.web_container_port
  protocol                 = "tcp"
  security_group_id        = aws_security_group.service.id
  source_security_group_id = aws_security_group.alb.id
  description              = "Web container port from the ALB"
}

# API paths stay on the API service; the listener default action (alb.tf) sends
# everything else to the web target group. Attaches to whichever listener is active
# (HTTPS with a cert, else HTTP).
resource "aws_lb_listener_rule" "api_paths" {
  count        = var.deploy_web ? 1 : 0
  listener_arn = coalesce(one(aws_lb_listener.https[*].arn), one(aws_lb_listener.http_forward[*].arn))
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  condition {
    path_pattern {
      values = ["/api/*", "/healthz", "/readyz"]
    }
  }
}

resource "aws_ecs_service" "web" {
  count           = var.deploy_web ? 1 : 0
  name            = "${local.name}-web"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.web[0].arn
  desired_count   = var.web_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.service.id]
    assign_public_ip = var.assign_public_ip
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.web[0].arn
    container_name   = "web"
    container_port   = var.web_container_port
  }

  lifecycle {
    ignore_changes = [desired_count]
  }

  depends_on = [aws_lb_listener_rule.api_paths]
}
