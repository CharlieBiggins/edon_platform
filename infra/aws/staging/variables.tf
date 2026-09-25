variable "aws_region" { type = string }
variable "name" { type = string default = "cerebrum-staging" }
variable "vpc_cidr" { type = string default = "10.42.0.0/16" }
variable "public_subnets" { type = list(string) default = ["10.42.1.0/24", "10.42.2.0/24"] }
variable "private_subnets" { type = list(string) default = ["10.42.11.0/24", "10.42.12.0/24"] }
variable "database_subnets" { type = list(string) default = ["10.42.21.0/24", "10.42.22.0/24"] }
variable "container_image" { type = string }
variable "worker_image" { type = string }
variable "oidc_issuer" { type = string }
variable "oidc_audience" { type = string }
variable "jwks_url" { type = string }
variable "github_repository" { type = string }
variable "route53_zone_id" { type = string default = "" }
variable "staging_hostname" { type = string default = "" }
variable "certificate_arn" { type = string }
variable "api_desired_count" { type = number default = 0 }
variable "worker_desired_count" { type = number default = 0 }
