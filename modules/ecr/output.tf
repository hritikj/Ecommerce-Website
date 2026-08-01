output "repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.game_repo.repository_url
}
