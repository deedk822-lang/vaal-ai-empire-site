#!/bin/bash
# Validate Alloy Configuration for Vaal AI Empire
# Checks syntax, environment variables, and connectivity

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ALLOY_DIR="$PROJECT_ROOT/observability/alloy"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FAILED=0

echo "=== Alloy Configuration Validator ==="
echo ""

# Check if alloy is installed
echo -n "Checking Alloy installation... "
if command -v alloy &> /dev/null; then
    ALLOY_VERSION=$(alloy --version 2>&1 | head -1)
    echo -e "${GREEN}✓${NC} $ALLOY_VERSION"
else
    echo -e "${RED}✗${NC} Alloy not found in PATH"
    echo "Install from: https://grafana.com/docs/alloy/latest/set-up/install/"
    exit 1
fi

# Check environment variables
echo ""
echo "Checking environment variables..."

REQUIRED_VARS=(
    "GCP_PROJECT_ID"
    "GITHUB_TOKEN"
    "ENVIRONMENT"
)

for var in "${REQUIRED_VARS[@]}"; do
    echo -n "  $var... "
    if [ -n "${!var}" ]; then
        echo -e "${GREEN}✓${NC} set"
    else
        echo -e "${YELLOW}⚠${NC} not set (will use defaults)"
    fi
done

# Check optional but recommended variables
echo ""
echo "Checking optional variables..."

OPTIONAL_VARS=(
    "GOOGLE_APPLICATION_CREDENTIALS"
    "HOSTNAME"
    "GCP_REGION"
    "STRIPE_ENVIRONMENT"
    "APP_VERSION"
)

for var in "${OPTIONAL_VARS[@]}"; do
    echo -n "  $var... "
    if [ -n "${!var}" ]; then
        echo -e "${GREEN}✓${NC} set"
    else
        echo -e "${YELLOW}⚠${NC} not set"
    fi
done

# Validate syntax of all .alloy files
echo ""
echo "Validating Alloy configuration files..."

for config_file in "$ALLOY_DIR"/*.alloy; do
    if [ -f "$config_file" ]; then
        filename=$(basename "$config_file")
        echo -n "  $filename... "
        
        if alloy fmt "$config_file" > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} syntax valid"
        else
            echo -e "${RED}✗${NC} syntax error"
            echo ""
            echo "Formatting output:"
            alloy fmt "$config_file" 2>&1 || true
            FAILED=1
        fi
    fi
done

# Check log file paths exist (if configured)
echo ""
echo "Checking log file paths..."

LOG_PATHS=(
    "/var/log/vaal-ai-empire"
    "/var/log/nginx"
)

for path in "${LOG_PATHS[@]}"; do
    echo -n "  $path... "
    if [ -d "$path" ]; then
        echo -e "${GREEN}✓${NC} exists"
    else
        echo -e "${YELLOW}⚠${NC} does not exist"
        echo "    Run: sudo mkdir -p $path && sudo chown alloy:alloy $path"
    fi
done

# Check GitHub token validity
echo ""
if [ -n "$GITHUB_TOKEN" ]; then
    echo -n "Checking GitHub token... "
    
    GH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        https://api.github.com/user)
    
    if [ "$GH_RESPONSE" == "200" ]; then
        echo -e "${GREEN}✓${NC} valid"
    else
        echo -e "${RED}✗${NC} invalid (HTTP $GH_RESPONSE)"
        FAILED=1
    fi
else
    echo "Skipping GitHub token check (not set)"
fi

# Check GCP connectivity
echo ""
if [ -n "$GCP_PROJECT_ID" ]; then
    echo -n "Checking GCP project access... "
    
    if command -v gcloud &> /dev/null; then
        if gcloud projects describe "$GCP_PROJECT_ID" > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} accessible"
            
            # Check Monitoring API
            echo -n "  Monitoring API... "
            if gcloud services list --enabled 2>/dev/null | grep -q monitoring.googleapis.com; then
                echo -e "${GREEN}✓${NC} enabled"
            else
                echo -e "${YELLOW}⚠${NC} not enabled"
                echo "    Run: gcloud services enable monitoring.googleapis.com"
            fi
            
            # Check Logging API
            echo -n "  Logging API... "
            if gcloud services list --enabled 2>/dev/null | grep -q logging.googleapis.com; then
                echo -e "${GREEN}✓${NC} enabled"
            else
                echo -e "${YELLOW}⚠${NC} not enabled"
                echo "    Run: gcloud services enable logging.googleapis.com"
            fi
        else
            echo -e "${RED}✗${NC} cannot access project"
            FAILED=1
        fi
    else
        echo -e "${YELLOW}⚠${NC} gcloud not installed, skipping"
    fi
else
    echo "Skipping GCP checks (GCP_PROJECT_ID not set)"
fi

# Dry-run test (if possible)
echo ""
echo "Running configuration dry-run..."

if [ -f "$ALLOY_DIR/github_exporter.alloy" ]; then
    echo -n "  Testing github_exporter.alloy... "
    
    # Run alloy with a timeout to catch config errors
    timeout 5s alloy run --stability.level=experimental \
        --server.http.listen-addr=localhost:12345 \
        "$ALLOY_DIR/github_exporter.alloy" > /tmp/alloy-test.log 2>&1 &
    
    ALLOY_PID=$!
    sleep 2
    
    if kill -0 $ALLOY_PID 2>/dev/null; then
        echo -e "${GREEN}✓${NC} starts successfully"
        kill $ALLOY_PID 2>/dev/null || true
        wait $ALLOY_PID 2>/dev/null || true
    else
        echo -e "${RED}✗${NC} failed to start"
        echo ""
        echo "Error log:"
        cat /tmp/alloy-test.log || true
        FAILED=1
    fi
fi

# Summary
echo ""
echo "========================================"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "You can now start Alloy with:"
    echo "  alloy run $ALLOY_DIR/github_exporter.alloy"
    echo ""
    echo "Or as a service:"
    echo "  sudo systemctl start alloy"
    exit 0
else
    echo -e "${RED}✗ Some checks failed.${NC}"
    echo "Please fix the errors above before starting Alloy."
    exit 1
fi
