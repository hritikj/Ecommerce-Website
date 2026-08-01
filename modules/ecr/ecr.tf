resource "aws_ecr_repository" "repo" {
  for_each =  toset(var.repository_names)
  name = each.value
}
