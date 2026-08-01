resource "aws_ecr_repository" "repo" {
  for_each =  toset(var.repo_name)
  name = each.value
}
