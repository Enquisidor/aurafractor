# ── GCS Buckets ────────────────────────────────────────────────────────────────

# Primary audio storage bucket
resource "google_storage_bucket" "audio" {
  name                        = "${var.project_id}-aurafractor-audio-${var.environment}"
  location                    = var.region
  force_destroy               = var.environment != "production"
  uniform_bucket_level_access = true

  labels = local.labels

  lifecycle_rule {
    action { type = "Delete" }
    condition {
      # Delete original uploads after 7 days (privacy policy)
      age                = 7
      matches_prefix     = ["tracks/"]
      matches_suffix     = ["/original"]
    }
  }

  lifecycle_rule {
    action { type = "Delete" }
    condition {
      # Delete extracted stems after 30 days (privacy policy)
      age            = 30
      matches_prefix = ["stems/"]
    }
  }

  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD"]
    response_header = ["Content-Type", "Content-Length"]
    max_age_seconds = 3600
  }
}

# CORS policy: API service account can read/write; public can read signed URLs
resource "google_storage_bucket_iam_member" "api_audio_rw" {
  bucket = google_storage_bucket.audio.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.api.email}"
}
