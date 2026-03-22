variable "project" {
  description = "Project name prefix for all resources"
  default     = "cloudsentinel"
}

variable "aws_region" {
  description = "AWS region to deploy to"
  default     = "us-east-1"
}

variable "db_password" {
  description = "RDS master password"
  sensitive   = true
}
