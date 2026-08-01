module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "20.15.0"

  # ✅ Correct argument (NOT "name")
  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  vpc_id     = var.vpc_id
  subnet_ids = var.subnet_ids

  # ✅ Correct for v20
  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true

  cluster_addons = {
    coredns    = {}
    kube-proxy = {}
    vpc-cni    = {}
  }

  eks_managed_node_groups = {
    default = {
      instance_types = [var.node_instance]

      min_size     = var.min_size
      max_size     = var.max_size
      desired_size = var.desired_size

      ami_type             = "AL2_x86_64"
      force_update_version = true
    }
  }
}
