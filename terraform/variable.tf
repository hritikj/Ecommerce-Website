variable "cluster_name" {
  type    = string
  default = "ecomm_Cluster"
}


variable "cluster_version" {
  type    = string
  default = "1.32"
}

variable "node_instance" {
  type    = string
  default = "t3.medium"
}

variable "desired_size" {
  type    = number
  default = 2
}

variable "min_size" {
  type    = number
  default = 1
}

variable "max_size" {
  type    = number
  default = 4
}

variable "repo_name" {
  type    = string
  default = "Terraform-project"
}
