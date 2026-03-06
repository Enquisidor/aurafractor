# ── Service Account ────────────────────────────────────────────────────────────

resource "google_service_account" "api" {
  account_id   = "aurafractor-api-${var.environment}"
  display_name = "Aurafractor API (${var.environment})"
}

# Roles the API service account needs
locals {
  api_roles = [
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/cloudtasks.enqueuer",
  ]
}

resource "google_project_iam_member" "api_roles" {
  for_each = toset(local.api_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.api.email}"
}

# ── Cloud Run Service ──────────────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "api" {
  name     = local.service_name
  location = var.region
  labels   = local.labels

  template {
    service_account = google_service_account.api.email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    # Cloud SQL sidecar connection
    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [var.db_connection_name]
      }
    }

    containers {
      image = var.image

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
        cpu_idle = true  # Only charge for CPU when handling requests
      }

      ports {
        container_port = 5000
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

      # Static env vars
      env {
        name  = "FLASK_ENV"
        value = var.environment == "production" ? "production" : "staging"
      }
      env {
        name  = "ENABLE_MOCK_RESPONSES"
        value = "false"
      }
      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.audio.name
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }
      env {
        name  = "CLOUD_TASKS_QUEUE"
        value = google_cloud_tasks_queue.extraction.name
      }

      # Secrets from Secret Manager
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = var.db_url_secret
            version = "latest"
          }
        }
      }
      env {
        name = "JWT_SECRET"
        value_source {
          secret_key_ref {
            secret  = var.jwt_secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "WORKER_SECRET"
        value_source {
          secret_key_ref {
            secret  = var.worker_secret_id
            version = "latest"
          }
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

# Allow unauthenticated public traffic (auth is handled in-app)
resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.api.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Outputs ────────────────────────────────────────────────────────────────────

output "api_url" {
  description = "Public URL of the deployed API"
  value       = google_cloud_run_v2_service.api.uri
}

output "audio_bucket" {
  description = "GCS bucket for audio files"
  value       = google_storage_bucket.audio.name
}

output "tasks_queue" {
  description = "Cloud Tasks queue name"
  value       = google_cloud_tasks_queue.extraction.name
}
