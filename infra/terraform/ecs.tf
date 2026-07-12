resource "aws_ecs_cluster" "main" {
  name = local.name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# Shared container scaffolding. Each task overrides `command` (except api, which uses
# the image's gunicorn default CMD) and its log group. Commands mirror the runtime
# services in docker-compose.yml (Django project package = "config"); reconcile there
# if the compose commands change.
locals {
  log_region = data.aws_region.current.name

  api_container = {
    name        = "api"
    image       = local.image
    essential   = true
    environment = local.container_environment
    secrets     = local.container_secrets
    portMappings = [{
      containerPort = var.api_container_port
      protocol      = "tcp"
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = local.log_region
        "awslogs-stream-prefix" = "api"
      }
    }
  }

  worker_container = {
    name             = "worker"
    image            = local.image
    essential        = true
    command          = ["celery", "-A", "config", "worker", "-l", "info"]
    environment      = local.container_environment
    secrets          = local.container_secrets
    logConfiguration = local.worker_log_config
  }

  worker_log_config = {
    logDriver = "awslogs"
    options = {
      "awslogs-group"         = aws_cloudwatch_log_group.worker.name
      "awslogs-region"        = local.log_region
      "awslogs-stream-prefix" = "worker"
    }
  }

  beat_container = {
    name        = "beat"
    image       = local.image
    essential   = true
    command     = ["celery", "-A", "config", "beat", "-l", "info"]
    environment = local.container_environment
    secrets     = local.container_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.beat.name
        "awslogs-region"        = local.log_region
        "awslogs-stream-prefix" = "beat"
      }
    }
  }

  # One-off schema task — deploy-prod-ecs.sh runs this per release (must be `migrate`,
  # never --run-syncdb) and asserts exit 0 before rolling the services.
  migrate_container = {
    name        = "migrate"
    image       = local.image
    essential   = true
    command     = ["python", "manage.py", "migrate", "--noinput"]
    environment = local.container_environment
    secrets     = local.container_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.migrate.name
        "awslogs-region"        = local.log_region
        "awslogs-stream-prefix" = "migrate"
      }
    }
  }
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions    = jsonencode([local.api_container])
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "${local.name}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions    = jsonencode([local.worker_container])
}

resource "aws_ecs_task_definition" "beat" {
  family                   = "${local.name}-beat"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions    = jsonencode([local.beat_container])
}

resource "aws_ecs_task_definition" "migrate" {
  family                   = "${local.name}-migrate"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions    = jsonencode([local.migrate_container])
}

# --- Services ------------------------------------------------------------------
resource "aws_ecs_service" "api" {
  name            = "${local.name}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.service.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = var.api_container_port
  }

  # deploy-prod-ecs.sh force-new-deployment rolls the mutable tag; ignore count drift
  # from any autoscaling and the task-def revision the deploy script bumps.
  lifecycle {
    ignore_changes = [desired_count]
  }

  depends_on = [aws_lb_listener.https, aws_lb_listener.http_forward]
}

resource "aws_ecs_service" "worker" {
  name            = "${local.name}-worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.worker_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.service.id]
    assign_public_ip = false
  }

  lifecycle {
    ignore_changes = [desired_count]
  }
}

resource "aws_ecs_service" "beat" {
  name            = "${local.name}-beat"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.beat.arn
  desired_count   = var.beat_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.service.id]
    assign_public_ip = false
  }
}
