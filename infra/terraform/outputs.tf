# These outputs map 1:1 to the environment scripts/deploy-prod-ecs.sh requires.

output "ecr_repository_url" {
  description = "api image repository URL (ASSEN_ECR_REPOSITORY_URI)."
  value       = local.image_repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name (ASSEN_ECS_CLUSTER)."
  value       = aws_ecs_cluster.main.name
}

output "ecs_api_service_name" {
  description = "API service name (ASSEN_ECS_API_SERVICE)."
  value       = aws_ecs_service.api.name
}

output "ecs_worker_service_name" {
  description = "Celery worker service name (ASSEN_ECS_WORKER_SERVICE)."
  value       = aws_ecs_service.worker.name
}

output "ecs_beat_service_name" {
  description = "Celery beat service name (ASSEN_ECS_BEAT_SERVICE)."
  value       = aws_ecs_service.beat.name
}

output "ecs_migrate_taskdef_family" {
  description = "One-off migrate task-definition family (ASSEN_ECS_MIGRATE_TASKDEF)."
  value       = aws_ecs_task_definition.migrate.family
}

output "alb_dns_name" {
  description = "ALB DNS name — point the production API host (ASSEN_PROD_API_URL) at this via DNS/ACM."
  value       = aws_lb.api.dns_name
}
