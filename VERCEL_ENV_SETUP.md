# VERCEL ENVIRONMENT VARIABLES
# Add these in Vercel Dashboard → Settings → Environment Variables
# You can import this as a .env file or add manually

# === REQUIRED FOR DEPLOYMENT ===

# Application
NODE_ENV=production
DOMAIN=https://vaal-ai-empire-site.vercel.app
STAGING_URL=https://vaal-ai-empire-site.vercel.app

# Auth
JWT_SECRET=vaal-empire-jwt-secret-production-2024

# CORS
ALLOWED_ORIGINS=https://vaal-ai-empire-site.vercel.app

# === AI API KEYS (copy values from GitHub Secrets) ===

CODERABBIT_API_KEY=[copy from GitHub secret]
DASHSCOPE_API_KEY=[copy from GitHub secret]
GLM5_API_KEY=[copy from GitHub secret]
KIMI_API_KEY=[copy from GitHub secret]
OLLAMA_API_KEY=[copy from GitHub secret]

# === OBSERVABILITY (copy values from GitHub Secrets) ===

PROMETHEUS_URL=[copy from GitHub secret]
PROMETHEUS_USER=[copy from GitHub secret]
PROMETHEUS_API_KEY=[copy from GitHub secret]
GRAFANA_API_KEY=[copy from GitHub secret]
GRAFANA_DATASOURCE_NAME=[copy from GitHub secret]
OPENTELEMETRY_API_KEY=[copy from GitHub secret]
PERPLEXITY_API_KEY=[copy from GitHub secret]

# === VERCEL ===

VERCEL_API_KEY=[copy from GitHub secret]
VERCEL_TOKEN=[copy from GitHub secret]

# === PAYFAST (configure later) ===

PAYFAST_MERCHANT_ID=10000100
PAYFAST_MERCHANT_KEY=
PAYFAST_PASSPHRASE=
PAYFAST_SANDBOX=true

# === PRICING ===

VAAL_STARTER_PRICE=99900
VAAL_EMPIRE_PRICE=299900
