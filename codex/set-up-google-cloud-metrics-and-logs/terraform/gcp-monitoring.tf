# Terraform Configuration for Google Cloud Monitoring
# Vaal AI Empire - Infrastructure as Code

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
  
  required_version = ">= 1.5.0"
}

# Variables
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment (production, staging, development)"
  type        = string
  default     = "production"
}

# Provider configuration
provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "monitoring" {
  service            = "monitoring.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "logging" {
  service            = "logging.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloudtrace" {
  service            = "cloudtrace.googleapis.com"
  disable_on_destroy = false
}

# Service Account for Alloy
resource "google_service_account" "alloy_monitoring" {
  account_id   = "alloy-monitoring-sa"
  display_name = "Alloy Monitoring Service Account"
  description  = "Service account for Grafana Alloy to write metrics and logs"
}

# IAM Roles for Service Account
resource "google_project_iam_member" "metric_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.alloy_monitoring.email}"
}

resource "google_project_iam_member" "log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.alloy_monitoring.email}"
}

resource "google_project_iam_member" "trace_agent" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.alloy_monitoring.email}"
}

# Log Sink for Vaal AI Empire
resource "google_logging_project_sink" "vaal_ai_empire" {
  name                   = "vaal-ai-empire-logs"
  destination            = "bigquery.googleapis.com/projects/${var.project_id}/datasets/vaal_ai_empire_logs"
  filter                 = <<-EOT
    resource.type="global"
    jsonPayload.service="vaal-ai-empire"
  EOT
  unique_writer_identity = true
}

# Custom Log-based Metric - Error Rate
resource "google_logging_metric" "error_rate" {
  name   = "vaal-ai-empire/error-count"
  filter = <<-EOT
    resource.type="global"
    jsonPayload.service="vaal-ai-empire"
    jsonPayload.level="error"
  EOT
  
  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "INT64"
    description  = "Count of error log entries"
    unit         = "1"
    
    labels {
      key         = "component"
      value_type  = "STRING"
      description = "Component that generated the error"
    }
  }
  
  label_extractors = {
    "component" = "EXTRACT(jsonPayload.component)"
  }
}

# Custom Log-based Metric - Response Time
resource "google_logging_metric" "response_time" {
  name   = "vaal-ai-empire/response-time"
  filter = <<-EOT
    resource.type="global"
    jsonPayload.service="vaal-ai-empire"
    jsonPayload.response_time_ms!=""
  EOT
  
  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "DISTRIBUTION"
    description  = "Response time distribution"
    unit         = "ms"
  }
  
  value_extractor = "EXTRACT(jsonPayload.response_time_ms)"
  
  bucket_options {
    exponential_buckets {
      num_finite_buckets = 64
      growth_factor      = 2
      scale              = 1
    }
  }
}

# Uptime Check - Main Website
resource "google_monitoring_uptime_check_config" "main_website" {
  display_name = "Vaal AI Empire - Main Website"
  timeout      = "10s"
  period       = "60s"
  
  http_check {
    path         = "/"
    port         = "443"
    use_ssl      = true
    validate_ssl = true
  }
  
  monitored_resource {
    type = "uptime_url"
    labels = {
      host       = "vaalaiempire.co.za"
      project_id = var.project_id
    }
  }
}

# Uptime Check - API Health
resource "google_monitoring_uptime_check_config" "api_health" {
  display_name = "Vaal AI Empire - API Health"
  timeout      = "10s"
  period       = "60s"
  
  http_check {
    path         = "/api/health"
    port         = "443"
    use_ssl      = true
    validate_ssl = true
  }
  
  monitored_resource {
    type = "uptime_url"
    labels = {
      host       = "vaalaiempire.co.za"
      project_id = var.project_id
    }
  }
}

# Alerting Policy - High Error Rate
resource "google_monitoring_alert_policy" "high_error_rate" {
  display_name = "High Error Rate"
  combiner     = "OR"
  
  conditions {
    display_name = "Error rate exceeds threshold"
    
    condition_threshold {
      filter          = <<-EOT
        resource.type="global"
        metric.type="logging.googleapis.com/user/vaal-ai-empire/error-count"
      EOT
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }
      comparison      = "COMPARISON_GT"
      threshold_value = 0.1
      duration        = "300s"
      
      trigger {
        count = 1
      }
    }
  }
  
  notification_channels = [google_monitoring_notification_channel.email.id]
  
  alert_strategy {
    auto_close = "86400s"
  }
  
  severity = "CRITICAL"
  
  documentation {
    content   = "Error rate is above 10% for 5 minutes. Check application logs immediately."
    mime_type = "text/markdown"
  }
}

# Alerting Policy - High Latency
resource "google_monitoring_alert_policy" "high_latency" {
  display_name = "High API Latency"
  combiner     = "OR"
  
  conditions {
    display_name = "95th percentile latency exceeds 2s"
    
    condition_threshold {
      filter          = <<-EOT
        resource.type="global"
        metric.type="logging.googleapis.com/user/vaal-ai-empire/response-time"
      EOT
      aggregations {
        alignment_period     = "600s"
        per_series_aligner   = "ALIGN_PERCENTILE_95"
      }
      comparison      = "COMPARISON_GT"
      threshold_value = 2000
      duration        = "600s"
      
      trigger {
        count = 1
      }
    }
  }
  
  notification_channels = [google_monitoring_notification_channel.email.id]
  
  alert_strategy {
    auto_close = "86400s"
  }
  
  severity = "WARNING"
  
  documentation {
    content   = "API response time is high. Consider scaling resources or investigating bottlenecks."
    mime_type = "text/markdown"
  }
}

# Alerting Policy - Website Down
resource "google_monitoring_alert_policy" "website_down" {
  display_name = "Website Down"
  combiner     = "OR"
  
  conditions {
    display_name = "Uptime check failed"
    
    condition_threshold {
      filter          = <<-EOT
        resource.type="uptime_url"
        metric.type="monitoring.googleapis.com/uptime_check/check_passed"
        metric.labels.check_id="${google_monitoring_uptime_check_config.main_website.id}"
      EOT
      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_FRACTION_TRUE"
        cross_series_reducer = "REDUCE_MEAN"
      }
      comparison      = "COMPARISON_LT"
      threshold_value = 0.5
      duration        = "0s"
      
      trigger {
        count = 1
      }
    }
  }
  
  notification_channels = [google_monitoring_notification_channel.email.id]
  
  alert_strategy {
    auto_close = "86400s"
  }
  
  severity = "CRITICAL"
  
  documentation {
    content   = "The main website is not responding. Check server status and network connectivity."
    mime_type = "text/markdown"
  }
}

# Notification Channel - Email
resource "google_monitoring_notification_channel" "email" {
  display_name = "Vaal AI Empire Alerts"
  type         = "email"
  
  labels = {
    email_address = "alerts@vaalaiempire.co.za"
  }
}

# Custom Dashboard - Application Overview
resource "google_monitoring_dashboard" "application_overview" {
  dashboard_json = jsonencode({
    displayName = "Vaal AI Empire - Application Overview"
    gridLayout = {
      columns = "2"
      widgets = [
        {
          title = "Error Rate"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"global\" metric.type=\"logging.googleapis.com/user/vaal-ai-empire/error-count\""
                  aggregation = {
                    alignmentPeriod    = "60s"
                    perSeriesAligner   = "ALIGN_RATE"
                  }
                }
              }
            }]
          }
        },
        {
          title = "Response Time (p95)"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"global\" metric.type=\"logging.googleapis.com/user/vaal-ai-empire/response-time\""
                  aggregation = {
                    alignmentPeriod    = "60s"
                    perSeriesAligner   = "ALIGN_PERCENTILE_95"
                  }
                }
              }
            }]
          }
        },
        {
          title = "Uptime Check Status"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"uptime_url\" metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\""
                }
              }
            }]
          }
        },
        {
          title = "CPU Utilization"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"compute.googleapis.com/instance/cpu/utilization\""
                }
              }
            }]
          }
        }
      ]
    }
  })
}

# Outputs
output "service_account_email" {
  description = "Email of the Alloy monitoring service account"
  value       = google_service_account.alloy_monitoring.email
}

output "uptime_check_main_website" {
  description = "ID of the main website uptime check"
  value       = google_monitoring_uptime_check_config.main_website.id
}

output "notification_channel_id" {
  description = "ID of the notification channel"
  value       = google_monitoring_notification_channel.email.id
}
