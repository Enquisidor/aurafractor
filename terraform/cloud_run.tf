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

      # Port must match the port gunicorn binds to in the Dockerfile CMD.
      # The Dockerfile sets ENV PORT=8080 and gunicorn binds to 0.0.0.0:8080.
      # Cloud Run also injects PORT=8080 by default.
      # Declaring 5000 here while the process listens on 8080 causes Cloud Run's
      # ingress to forward requests to a port with no listener, producing 502
      # responses that carry no CORS headers — the browser reports this as a
      # CORS error even though the Flask CORS configuration is correct.
      ports {
        container_port = 8080
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

      # Explicitly set allowed CORS origins so the value is auditable in IaC
      # and does not rely on the hardcoded default in backend/app.py.
      # The Flask app reads ALLOWED_ORIGINS as a comma-separated list.
      env {
        name  = "ALLOWED_ORIGINS"
        value = var.allowed_origins
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

# ── Custom Domain Mapping ──────────────────────────────────────────────────────
#
# Maps api.aurafractor.com to this Cloud Run service.
#
# IMPORTANT — DNS verification required after first apply:
#   After `terraform apply`, run:
#     gcloud beta run domain-mappings describe \
#       --domain=api.aurafractor.com \
#       --region=<region> \
#       --project=<project>
#   and add the returned A/AAAA or CNAME records to your DNS provider.
#   Until DNS propagates, the domain will return a Google verification page,
#   not the Flask app — this will appear as a CORS error to the browser.
#
# Cloud Run domain mappings only support regions where the feature is available.
# If your region does not support domain mappings, use a Cloud Load Balancer
# with a serverless NEG backend instead (flag this for tech lead review).
#
# This resource is only created when var.api_custom_domain is non-empty.
# Set it to "" in tfvars to skip domain mapping for environments without a
# custom domain.

resource "google_cloud_run_domain_mapping" "api" {
  count    = var.api_custom_domain != "" ? 1 : 0
  name     = var.api_custom_domain
  location = var.region

  metadata {
    namespace = var.project_id
    labels    = local.labels
  }

  spec {
    route_name = google_cloud_run_v2_service.api.name
  }
}

# ── Outputs ────────────────────────────────────────────────────────────────────

output "api_url" {
  description = "Public URL of the deployed API (Cloud Run generated URL)"
  value       = google_cloud_run_v2_service.api.uri
}

output "api_custom_domain_url" {
  description = "Custom domain URL for the API (if configured)"
  value       = var.api_custom_domain != "" ? "https://${var.api_custom_domain}" : "not configured"
}

output "audio_bucket" {
  description = "GCS bucket for audio files"
  value       = google_storage_bucket.audio.name
}

output "tasks_queue" {
  description = "Cloud Tasks queue name"
  value       = google_cloud_tasks_queue.extraction.name
}
