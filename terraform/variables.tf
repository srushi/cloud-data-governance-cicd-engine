variable "project_id" {
  description = "GCP project that hosts the validation service."
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run, Scheduler and Artifact Registry."
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Name of the validation service / job resources."
  type        = string
  default     = "data-governance-validator"
}

variable "image" {
  description = "Container image for the validation engine (Artifact Registry)."
  type        = string
  default     = "us-central1-docker.pkg.dev/example/validators/engine:latest"
}

variable "audit_source" {
  description = "Warehouse the scheduled audit targets (snowflake | bigquery)."
  type        = string
  default     = "bigquery"
}

variable "schedule_cron" {
  description = "Cron schedule for the daily warehouse audit (UTC)."
  type        = string
  default     = "0 2 * * *"
}
