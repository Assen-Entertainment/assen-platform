resource "aws_lb" "api" {
  name               = "${local.name}-api"
  load_balancer_type = "application"
  internal           = false
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids

  # 120s, deliberately raised from the 60s default: every media byte crosses this ALB.
  # Media is proxied through the app tier (apps/uploads/media.py) rather than read
  # bucket-direct, so a whole object — up to UPLOAD_MAX_BYTES, 10 MiB by default —
  # streams through here on the way out, and the same size streams in on upload.
  #
  # What this does NOT protect against is a merely *slow* client: the idle timer fires
  # only when no bytes move for the entire window, and a sustained slow transfer resets
  # it on every 64 KiB chunk. The case 60s is genuinely too tight for is a STALL — a
  # mobile client that pauses mid-transfer (cell handoff, tunnel, app backgrounded) and
  # resumes to find the ALB already tore the connection down. Outbound that is a broken
  # image; inbound it is a 10 MiB body the fan has to send again. 120s rides out a
  # stall of that shape.
  #
  # 120 and not more: nothing on this listener is long-poll or SSE, so a connection
  # idle beyond ~2 minutes is a dead peer rather than slow progress, and holding it
  # open just consumes an ALB connection slot. (The 4000s ceiling would be inventing a
  # requirement no route here has.) WebSockets share this listener via Channels and are
  # unaffected either way — daphne pings every 20s (--ping-interval default), far
  # inside this window.
  #
  # Safe to raise specifically because of how the target behaves: the classic 502 from
  # a raised idle timeout comes from the ALB reusing a keep-alive connection the target
  # closed first, which needs the target's keep-alive to be SHORTER than this value.
  # Daphne's --http-timeout defaults to None and server/Dockerfile's CMD does not set
  # it, so the target never closes an idle HTTP connection first — the race needs the
  # opposite ordering. Re-check this if the app server or its flags ever change.
  idle_timeout = 120
}

# Target group for the API tasks (ip target type for Fargate awsvpc). Health check
# hits /healthz — the same endpoint scripts/deploy-prod-ecs.sh smokes.
resource "aws_lb_target_group" "api" {
  name        = "${local.name}-api"
  port        = var.api_container_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    path                = "/healthz"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

# HTTPS listener when an ACM cert is provided (production).
resource "aws_lb_listener" "https" {
  count = var.acm_certificate_arn != "" ? 1 : 0

  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.acm_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = var.deploy_web ? one(aws_lb_target_group.web[*].arn) : aws_lb_target_group.api.arn
  }
}

# With a cert, plain HTTP redirects to HTTPS.
resource "aws_lb_listener" "http_redirect" {
  count = var.acm_certificate_arn != "" ? 1 : 0

  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# Without a cert (non-production only), forward HTTP straight to the API.
resource "aws_lb_listener" "http_forward" {
  count = var.acm_certificate_arn == "" ? 1 : 0

  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = var.deploy_web ? one(aws_lb_target_group.web[*].arn) : aws_lb_target_group.api.arn
  }
}
