# Grafana Cloud Metrics Integration (OTLP)

This document describes how metrics are sent from the Vaal AI Empire application to Grafana Cloud using **OpenTelemetry Protocol (OTLP)**.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   GitHub Actions │────▶│  Grafana Cloud  │     │  Alibaba Cloud  │
│    CI/CD Pipeline│     │   OTLP Gateway  │◄────│   Staging Env   │
└─────────────────┘     │  (Singapore)    │     └─────────────────┘
                        └─────────────────┘              │
                                ▲                        │
                                │              ┌─────────┴─────────┐
                                │              │  Grafana Agent    │
                                └──────────────│   (OTLP Export)   │
                                               └───────────────────┘
                                                      │
                                               ┌──────▼──────┐
                                               │  Node.js App │
                                               │  /metrics   │
                                               └─────────────┘
```

## Configuration

### Grafana Cloud Details (Singapore Region)

| Setting | Value |
|---------|-------|
| **Region** | prod-ap-southeast-1 |
| **OTLP Endpoint** | `https://otlp-gateway-prod-ap-southeast-1.grafana.net/otlp` |
| **Instance ID** | `1397265` |
| **API Token** | Stored in GitHub Secrets as `GRAFANA_CLOUD_API_KEY` |

**Why OTLP?**
- Modern OpenTelemetry standard
- Supports metrics, traces, and logs in one protocol
- Better compression and efficiency
- Future-proof observability stack

### Metrics Collection via OTLP

#### 1. Application Metrics (Node.js)
The application exposes Prometheus-format metrics at `/metrics`:

```bash
curl http://localhost:4242/metrics
```

Available metrics:
- `vaal_ai_empire_http_request_duration_seconds` - HTTP request latency
- `vaal_ai_empire_http_requests_total` - Total HTTP requests
- `vaal_ai_empire_active_connections` - Active connections
- `vaal_ai_empire_stripe_webhook_events_total` - Stripe webhook events
- `vaal_ai_empire_checkout_sessions_created_total` - Checkout sessions
- Default Node.js metrics (CPU, memory, GC, event loop)

#### 2. Grafana Agent Sidecar (OTLP Export)
The Grafana Agent runs as a sidecar container that:
- Scrapes metrics from the app every 15s
- **Converts to OTLP format**
- **Pushes metrics to Grafana Cloud OTLP Gateway**
- Handles authentication with Instance ID + API Key

#### 3. CI/CD Metrics (OTLP)
GitHub Actions sends build metrics via OTLP after each workflow run:
- `vaal_ai_empire_build_total` - Build counter
- `vaal_ai_empire_build_success` - Build success rate
- `vaal_ai_empire_deployment_total` - Deployment counter
- `vaal_ai_empire_deployment_success` - Deployment success rate

## GitHub Secrets Required

Add these secrets to your GitHub repository:

| Secret Name | Description |
|-------------|-------------|
| `GRAFANA_CLOUD_API_KEY` | Your Grafana Cloud API token |
| `STRIPE_SECRET_KEY` | Stripe secret key |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key |
| `MONGODB_URI` | MongoDB connection string |
| `JWT_SECRET` | JWT signing secret |

## Deployment

The workflow automatically:
1. Builds the Docker image
2. Sends CI/CD metrics to Grafana Cloud
3. Deploys to Alibaba Cloud with Grafana Agent sidecar
4. Application metrics are scraped and pushed continuously

## Dashboard Access

Access your metrics at:
- **Grafana Cloud**: https://dimakatsomoleli.grafana.net
- **Data Source**: grafanacloud-dimakatsomoleli-prom

## Testing Metrics

To verify metrics are being received:

```bash
# Check application metrics endpoint
curl http://your-server:4242/metrics

# Query Grafana Cloud using OTLP (requires API key)
curl -H "Authorization: Basic $(echo -n '1397265:$GRAFANA_CLOUD_API_KEY' | base64)" \
  "https://prometheus-prod-37-prod-ap-southeast-1.grafana.net/api/prom/api/v1/query?query=up"

# Test OTLP endpoint directly
curl -X POST "https://otlp-gateway-prod-ap-southeast-1.grafana.net/otlp/v1/metrics" \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic $(echo -n '1397265:$GRAFANA_CLOUD_API_KEY' | base64)" \
  -d '{"resourceMetrics":[]}'
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No metrics in Grafana | Check Grafana Agent logs: `docker logs grafana-agent` |
| 401 Unauthorized | Verify `GRAFANA_CLOUD_API_KEY` and Instance ID (1397265) |
| 404 Not Found | Check OTLP endpoint URL is correct |
| Metrics not scraping | Ensure app is running and `/metrics` is accessible |
| High latency | Check network connectivity to Singapore region |
| OTLP conversion errors | Check Grafana Agent config for otelcol receiver |

### Verify OTLP Authentication

```bash
# Encode credentials
export AUTH=$(echo -n "1397265:$GRAFANA_CLOUD_API_KEY" | base64)

# Test OTLP endpoint
curl -v -X POST "https://otlp-gateway-prod-ap-southeast-1.grafana.net/otlp/v1/metrics" \
  -H "Authorization: Basic $AUTH" \
  -H "Content-Type: application/json" \
  -d '{"resourceMetrics":[]}'
```

## Cost Considerations

Grafana Cloud pricing is based on:
- **Active Series**: Currently 0 (within free tier)
- **Data Retention**: 30 days on free tier
- **Query Volume**: Unlimited on paid plans

Monitor your usage at: https://grafana.com/profile/org/usage
