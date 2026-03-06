terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Uncomment to store state in GCS (recommended for teams)
  # backend "gcs" {
  #   bucket = "your-tfstate-bucket"
  #   prefix = "aurafractor/backend"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ── Shared locals ──────────────────────────────────────────────────────────────

locals {
  service_name = "aurafractor-api"
  labels = {
    app     = "aurafractor"
    managed = "terraform"
  }
}
