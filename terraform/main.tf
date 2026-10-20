terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Artifact Registry repository that stores the engine's container images.
resource "google_artifact_registry_repository" "engine" {
  location      = var.region
  repository_id = "validators"
  format        = "DOCKER"
  description   = "Container images for the data governance validation engine."
}

# Bucket where exception logs and audit reports are published.
resource "google_storage_bucket" "reports" {
  name                        = "${var.project_id}-${var.service_name}-reports"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}

# Dedicated service account the validation workloads run as.
resource "google_service_account" "validator" {
  account_id   = var.service_name
  display_name = "Data Governance Validator"
}

resource "google_storage_bucket_iam_member" "reports_writer" {
  bucket = google_storage_bucket.reports.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.validator.email}"
}

resource "google_project_iam_member" "bigquery_reader" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.validator.email}"
}

# Report server: serves the latest summary.json at /summary (see engine/server.py).
resource "google_cloud_run_v2_service" "report_server" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.validator.email
    containers {
      image = var.image
      args  = ["-m", "engine.server", "--port", "8080", "--report-dir", "/data/out"]
      ports {
        container_port = 8080
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }
  }
}

# Scheduled audit job: runs the engine CLI against the warehouse.
resource "google_cloud_run_v2_job" "audit" {
  name     = "${var.service_name}-audit"
  location = var.region

  template {
    template {
      service_account = google_service_account.validator.email
      containers {
        image = var.image
        args = [
          "run-audit",
          "--source", var.audit_source,
          "--report", "/data/out",
          "--fail-on-critical",
        ]
        env {
          name  = "BIGQUERY_PROJECT"
          value = var.project_id
        }
      }
    }
  }
}

# Cloud Scheduler triggers the audit job every night.
resource "google_cloud_scheduler_job" "daily_audit" {
  name     = "${var.service_name}-daily"
  region   = var.region
  schedule = var.schedule_cron
  time_zone = "Etc/UTC"

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.audit.name}:run"

    oauth_token {
      service_account_email = google_service_account.validator.email
    }
  }

  retry_config {
    retry_count = 1
  }
}
