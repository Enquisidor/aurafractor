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

variable "api_custom_domain" {
  description = "Custom domain for the API service (e.g. api.aurafractor.com). Set to empty string to skip domain mapping."
  type        = string
  default     = ""
}

variable "allowed_origins" {
  description = "Comma-separated list of allowed CORS origins for the API. Passed to Flask as ALLOWED_ORIGINS."
  type        = string
  default     = "https://aurafractor.web.app,https://aurafractor.firebaseapp.com"
}

# TODO: A dedicated ML worker Cloud Run service must be provisioned before this
# variable can be set to a real value. The worker service is not yet defined in
# this Terraform configuration. When it is created, set worker_url to the Cloud
# Run service URI (format: https://<service>-<hash>-<region>.a.run.app) or to
# the custom domain mapped to it. Until the worker service exists and this
# variable is set, the API will default to http://localhost:5001/worker/extract
# and all extraction jobs will fail silently after 3 Cloud Tasks retries.
variable "worker_url" {
  description = "Full HTTPS URL of the ML worker Cloud Run service that Cloud Tasks will POST extraction jobs to (e.g. https://aurafractor-worker-<hash>-uc.a.run.app/worker/extract). Leave empty until the worker service is provisioned."
  type        = string
  default     = ""
}
