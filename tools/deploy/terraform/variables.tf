variable "project_id" {
  type        = string
  description = "GCP project ID for the lab."
}

variable "region" {
  type        = string
  default     = "us-central1"
  description = "Region for the VPC, subnets, router/NAT, and DB VM."
}

variable "zone" {
  type        = string
  default     = "us-central1-c"
  description = "Zone for the DB VM and its data disk."
}

variable "db_machine_type" {
  type        = string
  default     = "e2-standard-4"
  description = "Machine type for the coffee-db VM (standard, non-Spot)."
}

variable "db_data_disk_size_gb" {
  type        = number
  default     = 50
  description = "Size of the persistent pd-ssd Oracle data disk."
}

variable "cos_image_family" {
  type        = string
  default     = "cos-stable"
  description = "Container-Optimized OS image family for the DB VM."
}

variable "db_password_secret_id" {
  type        = string
  default     = "coffee-db-password"
  description = "Secret Manager secret holding the Oracle APP user password (created in Ch3)."
}

variable "system_password_secret_id" {
  type        = string
  default     = "coffee-db-system-password"
  description = "Secret Manager secret holding the Oracle SYS/SYSTEM password (created in Ch3)."
}

variable "db_password" {
  type        = string
  description = "Oracle APP-user password (DATABASE_PASSWORD). Consumed by Cloud Run, the build migrate step, and the DB VM app user. LAB ONLY: set in gitignored terraform.tfvars."
  sensitive   = true
}

variable "db_system_password" {
  type        = string
  description = "Oracle SYS/system password. Consumed ONLY by the Ch2 DB VM cloud-init at boot; never reaches Cloud Run or the build pool. LAB ONLY: set in gitignored terraform.tfvars."
  sensitive   = true
}

