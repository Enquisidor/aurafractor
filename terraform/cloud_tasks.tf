# ── Cloud Tasks ────────────────────────────────────────────────────────────────

resource "google_cloud_tasks_queue" "extraction" {
  name     = "aurafractor-extraction-${var.environment}"
  location = var.region

  rate_limits {
    max_concurrent_dispatches = 4   # matches MAX_CONCURRENT_EXTRACTIONS constraint
    max_dispatches_per_second = 2
  }

  retry_config {
    max_attempts       = 3
    max_retry_duration = "3600s"  # 1 hour total retry window
    min_backoff        = "30s"
    max_backoff        = "300s"
    max_doublings      = 3
  }

  stackdriver_logging_config {
    sampling_ratio = 1.0
  }
}

# Grant the API service account permission to enqueue tasks
resource "google_cloud_tasks_queue_iam_member" "api_enqueue" {
  name     = google_cloud_tasks_queue.extraction.name
  location = var.region
  role     = "roles/cloudtasks.enqueuer"
  member   = "serviceAccount:${google_service_account.api.email}"
}
