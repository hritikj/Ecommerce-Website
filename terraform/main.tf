module "ecr" {
  source  = "../modules/ecr"
  repo_name = [
   "fieldstead-auth",
   "fieldstead-products",
   "fieldstead-cart",
   "fieldstead-orders",
   "fieldstead-gateway",
   "fieldstead-frontend",
   "fieldstead-nginx",
   "fieldstead-mysql"
  ]
}

module "eks" {
  source  = "../modules/eks"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  node_instance = var.node_instance
  min_size      = var.min_size
  max_size      = var.max_size
  desired_size  = var.desired_size

}

module "vpc" {
  source = "../modules/vpc"
}
