output "report_bucket" {
  description = "GCS bucket where audit reports are published."
  value       = google_storage_bucket.reports.name
}

output "report_server_uri" {
  description = "URL of the Cloud Run report server (/summary, /health)."
  value       = google_cloud_run_v2_service.report_server.uri
}

output "audit_job_name" {
  description = "Cloud Run job that executes the warehouse audit."
  value       = google_cloud_run_v2_job.audit.name
}

output "scheduler_job_name" {
  description = "Cloud Scheduler job that triggers the nightly audit."
  value       = google_cloud_scheduler_job.daily_audit.name
}

output "service_account_email" {
  description = "Service account the validation workloads run as."
  value       = google_service_account.validator.email
}
