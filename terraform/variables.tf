variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for all resources"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Deployment environment (staging | production)"
  type        = string
  default     = "staging"
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production"
  }
}

variable "image" {
  description = "Full Docker image URI for the API service (e.g. gcr.io/PROJECT/aurafractor-api:TAG)"
  type        = string
}

variable "db_connection_name" {
  description = "Cloud SQL instance connection name (PROJECT:REGION:INSTANCE)"
  type        = string
}

variable "db_url_secret" {
  description = "Secret Manager secret ID containing the DATABASE_URL"
  type        = string
  default     = "aurafractor-db-url"
}

variable "jwt_secret_id" {
  description = "Secret Manager secret ID containing the JWT_SECRET"
  type        = string
  default     = "aurafractor-jwt-secret"
}

variable "worker_secret_id" {
  description = "Secret Manager secret ID containing the WORKER_SECRET"
  type        = string
  default     = "aurafractor-worker-secret"
}

variable "min_instances" {
  description = "Minimum Cloud Run instances (set > 0 to avoid cold starts)"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum Cloud Run instances"
  type        = number
  default     = 10
}
