terraform {
  backend "s3" {
    bucket         = "eks-ecomm-terraform-state"
    key            = "eks-ecomm/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "eks-ecomm-terraform-lock"
    encrypt        = true
  }
}
