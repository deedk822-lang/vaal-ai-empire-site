# Google Cloud Metrics and Logs Setup

Complete observability stack for Vaal AI Empire using Google Cloud Monitoring and Grafana Alloy.

## 📁 Directory Structure

```
codex/set-up-google-cloud-metrics-and-logs/
├── README.md                           # This file
├── observability/
│   └── alloy/
│       ├── github_exporter.alloy       # GitHub + App metrics & logs config
│       └── cloud_monitoring.alloy      # GCP-specific monitoring
├── scripts/
│   ├── install-alloy.sh               # Alloy installation script
│   ├── setup-gcp-credentials.sh       # GCP authentication setup
│   └── validate-config.sh             # Configuration validator
├── terraform/
│   └── gcp-monitoring.tf              # Infrastructure as Code
└── dashboards/
    ├── github-metrics.json            # GitHub repository dashboard
    ├── application-metrics.json        # App performance dashboard
    └── system-metrics.json            # Infrastructure dashboard
```

## 🚀 Quick Start

### 1. Prerequisites

- Google Cloud Project with Monitoring API enabled
- GitHub Personal Access Token with `repo` scope
- Service account with Monitoring Metric Writer and Logs Writer roles

### 2. Environment Variables

```bash
# Required
export GCP_PROJECT_ID="your-gcp-project-id"
export GITHUB_TOKEN="ghp_your_github_token"
export ENVIRONMENT="production"
export HOSTNAME="vaal-ai-empire-prod"

# For authentication (pick one method)
# Method 1: Service Account Key
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"

# Method 2: Access Token (short-lived)
export GCP_ACCESS_TOKEN="$(gcloud auth print-access-token)"
```

### 3. Install Grafana Alloy

```bash
cd codex/set-up-google-cloud-metrics-and-logs
chmod +x scripts/install-alloy.sh
sudo ./scripts/install-alloy.sh
```

### 4. Validate Configuration

```bash
chmod +x scripts/validate-config.sh
./scripts/validate-config.sh
```

### 5. Start Alloy

```bash
# Run in foreground for testing
sudo alloy run observability/alloy/github_exporter.alloy

# Or run as a service
sudo systemctl enable alloy
sudo systemctl start alloy
sudo systemctl status alloy
```

## 📊 Metrics Collected

### GitHub Metrics
- Repository stars, forks, watchers
- Open/closed issues and PRs
- Workflow run status and duration
- Release download counts

### Application Metrics (Node.js)
- HTTP request rate and latency
- Error rates
- Active connections
- Stripe webhook processing metrics

### System Metrics
- CPU usage
- Memory utilization
- Disk I/O
- Network throughput

## 📝 Logs Collected

### Application Logs
- `/var/log/vaal-ai-empire/app.log` - General application logs
- `/var/log/vaal-ai-empire/error.log` - Error logs

### System Logs
- `/var/log/nginx/*.log` - Web server access/error logs
- `/var/log/auth.log` - Authentication logs

## 🔧 Configuration Details

### Alloy Components

| Component | Purpose |
|-----------|---------|
| `prometheus.exporter.github` | Exports GitHub API metrics |
| `prometheus.exporter.unix` | System-level metrics |
| `prometheus.scrape` | Collects metrics from exporters |
| `prometheus.relabel` | Adds metadata labels |
| `prometheus.remote_write` | Sends metrics to Google Cloud |
| `loki.source.file` | Tails log files |
| `loki.process` | Parses and enriches logs |
| `loki.write` | Sends logs to Google Cloud |

### Scrape Intervals

| Job | Interval |
|-----|----------|
| github-exporter | 5 minutes |
| application | 30 seconds |
| node-exporter | 15 seconds |
| alloy-internal | 15 seconds |

## 🔐 Security

### Required GCP IAM Roles

```bash
# For the service account
roles/monitoring.metricWriter      # Write metrics
roles/logging.logWriter            # Write logs
roles/monitoring.viewer            # Read dashboards
```

### Required GitHub Token Scopes

- `repo` - Repository access
- `read:packages` - Package metrics (optional)

## 📈 Dashboards

Import the provided dashboards to Google Cloud Monitoring:

```bash
# Using gcloud CLI
gcloud monitoring dashboards create --config-from-file=dashboards/github-metrics.json
```

## 🐛 Troubleshooting

### Check Alloy Status

```bash
sudo systemctl status alloy
sudo journalctl -u alloy -f
```

### Test Configuration

```bash
# Validate Alloy syntax
alloy fmt observability/alloy/github_exporter.alloy
alloy run --stability.level=experimental observability/alloy/github_exporter.alloy
```

### Verify Metrics in GCP

```bash
# List available metrics
gcloud monitoring metrics list --filter="metric.type:starts_with('custom.googleapis.com')"

# Query metrics
gcloud monitoring metrics list --filter="github"
```

## 📚 References

- [Grafana Alloy Documentation](https://grafana.com/docs/alloy/)
- [Google Cloud Monitoring](https://cloud.google.com/monitoring/docs)
- [GitHub Prometheus Exporter](https://github.com/grafana/alloy/tree/main/internal/static/integrations/github_exporter)
- [Vaal AI Empire Architecture](../../ARCHITECTURE.md)

## 🔗 Related Files

- Main application: `../../server/routes/observability.js`
- Agent libraries: `../../agents/README.md`
- Backend setup: `../../BACKEND_SETUP.md`
