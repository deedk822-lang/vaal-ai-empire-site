#!/bin/bash
# Setup Google Cloud credentials for Alloy
# Vaal AI Empire - GCP Monitoring Integration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_DIR="/etc/alloy"

echo "=== Google Cloud Credentials Setup ==="
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed."
    echo "Please install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is authenticated
echo "Checking GCP authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | grep -q "@"; then
    echo "Not authenticated. Running 'gcloud auth login'..."
    gcloud auth login
fi

ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1)
echo "Authenticated as: $ACCOUNT"
echo ""

# Get or select project
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ -z "$CURRENT_PROJECT" ]; then
    echo "No project set. Available projects:"
    gcloud projects list --format="table(projectId,name)" --limit=10
    echo ""
    read -p "Enter project ID: " PROJECT_ID
    gcloud config set project "$PROJECT_ID"
else
    echo "Current project: $CURRENT_PROJECT"
    read -p "Use this project? (Y/n): " USE_CURRENT
    if [[ "$USE_CURRENT" =~ ^[Nn]$ ]]; then
        gcloud projects list --format="table(projectId,name)" --limit=10
        echo ""
        read -p "Enter project ID: " PROJECT_ID
        gcloud config set project "$PROJECT_ID"
    fi
fi

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
echo "Using project: $PROJECT_ID"
echo ""

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable monitoring.googleapis.com
gcloud services enable logging.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
echo "APIs enabled."
echo ""

# Create service account
SA_NAME="alloy-monitoring-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Setting up service account: $SA_NAME"

# Check if service account exists
if gcloud iam service-accounts list --filter="email:$SA_EMAIL" --format="value(email)" | grep -q "$SA_EMAIL"; then
    echo "Service account already exists: $SA_EMAIL"
else
    echo "Creating service account..."
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name="Alloy Monitoring Service Account" \
        --description="Service account for Grafana Alloy to write metrics and logs"
fi

# Grant required roles
echo "Granting IAM roles..."

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/monitoring.metricWriter" \
    --condition=None

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/logging.logWriter" \
    --condition=None

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/cloudtrace.agent" \
    --condition=None

echo "Roles granted."
echo ""

# Create and download service account key
KEY_FILE="${PROJECT_ROOT}/.credentials/${PROJECT_ID}-alloy-sa-key.json"
mkdir -p "$(dirname "$KEY_FILE")"

echo "Creating service account key..."
gcloud iam service-accounts keys create "$KEY_FILE" \
    --iam-account="$SA_EMAIL" \
    --key-file-type="json"

echo "Key saved to: $KEY_FILE"
echo ""

# Set permissions
chmod 600 "$KEY_FILE"

# Create environment file for Alloy
echo "Creating environment file..."

ENV_FILE="${CONFIG_DIR}/gcp-env"
if [ ! -d "$CONFIG_DIR" ]; then
    ENV_FILE="${PROJECT_ROOT}/.credentials/gcp-env"
    mkdir -p "$(dirname "$ENV_FILE")"
fi

cat > "$ENV_FILE" <<EOF
# Google Cloud Configuration for Alloy
# Generated on $(date)

GCP_PROJECT_ID=$PROJECT_ID
GOOGLE_APPLICATION_CREDENTIALS=$KEY_FILE
GCP_REGION=$(gcloud config get-value compute/region 2>/dev/null || echo "us-central1")
ENVIRONMENT=production
HOSTNAME=$(hostname)
EOF

chmod 600 "$ENV_FILE"
echo "Environment file created: $ENV_FILE"
echo ""

# Test credentials
echo "Testing credentials..."
export GOOGLE_APPLICATION_CREDENTIALS="$KEY_FILE"
if gcloud auth activate-service-account --key-file="$KEY_FILE" 2>/dev/null; then
    gcloud auth revoke "$SA_EMAIL" 2>/dev/null || true
    gcloud auth login --brief 2>/dev/null || true
    echo "✓ Credentials are valid"
else
    echo "✗ Failed to validate credentials"
    exit 1
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Service Account: $SA_EMAIL"
echo "Key File: $KEY_FILE"
echo ""
echo "Add this to your Alloy environment:"
echo "  export GOOGLE_APPLICATION_CREDENTIALS=$KEY_FILE"
echo "  export GCP_PROJECT_ID=$PROJECT_ID"
echo ""
echo "Or source the environment file:"
echo "  source $ENV_FILE"
echo ""
echo "To get an access token for testing:"
echo "  gcloud auth print-access-token"
