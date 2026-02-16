#!/bin/bash
# Vaal AI Empire - Ollama Setup Script
# Sets up Ollama with Kimi K2.5, GLM-5, and other models for benchmarking

set -e

echo "🦙 Setting up Ollama for Vaal AI Benchmark..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored status
print_status() {
    if [ "$1" = "success" ]; then
        echo -e "${GREEN}✅ $2${NC}"
    elif [ "$1" = "warning" ]; then
        echo -e "${YELLOW}⚠️  $2${NC}"
    elif [ "$1" = "error" ]; then
        echo -e "${RED}❌ $2${NC}"
    else
        echo "ℹ️  $2"
    fi
}

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    print_status "warning" "This script is designed for Linux. For macOS/Windows, see: https://ollama.com/download"
fi

# Step 1: Check if Ollama is installed
echo ""
echo "Step 1: Checking Ollama installation..."
if command -v ollama &> /dev/null; then
    OLLAMA_VERSION=$(ollama --version 2>/dev/null || echo "unknown")
    print_status "success" "Ollama is installed ($OLLAMA_VERSION)"
else
    print_status "info" "Ollama not found. Installing..."
    
    # Install Ollama
    if curl -fsSL https://ollama.com/install.sh | sh; then
        print_status "success" "Ollama installed successfully"
    else
        print_status "error" "Failed to install Ollama"
        echo "Please install manually: curl -fsSL https://ollama.com/install.sh | sh"
        exit 1
    fi
fi

# Step 2: Start Ollama daemon
echo ""
echo "Step 2: Starting Ollama daemon..."
if pgrep -x "ollama" > /dev/null; then
    print_status "success" "Ollama daemon is already running"
else
    print_status "info" "Starting Ollama daemon..."
    
    # Start ollama serve in background
    nohup ollama serve > /dev/null 2>&1 &
    sleep 3
    
    if pgrep -x "ollama" > /dev/null; then
        print_status "success" "Ollama daemon started"
    else
        print_status "error" "Failed to start Ollama daemon"
        echo "Try running: ollama serve &"
        exit 1
    fi
fi

# Step 3: Check for Ollama Cloud authentication
echo ""
echo "Step 3: Checking Ollama Cloud authentication..."
if ollama show --system 2>/dev/null | grep -q "cloud"; then
    print_status "success" "Ollama Cloud is configured"
else
    print_status "warning" "Ollama Cloud not configured (optional)"
    echo ""
    echo "For cloud models (Kimi K2.5, etc.), authenticate with:"
    echo "  ollama signin"
    echo ""
fi

# Step 4: Define models to pull
echo ""
echo "Step 4: Pulling AI models..."
echo ""

# Models configuration
declare -A MODELS
MODELS["kimi-k2.5"]="kimi-k2.5:cloud"
MODELS["glm-5"]="glm5"
MODELS["qwen2.5-coder"]="qwen2.5-coder:14b"
MODELS["llama3.2"]="llama3.2:latest"
MODELS["deepseek-coder"]="deepseek-coder:6.7b"

# Track success/failures
PULLED=0
FAILED=0

for name in "${!MODELS[@]}"; do
    model="${MODELS[$name]}"
    echo "📦 Pulling $name ($model)..."
    
    if ollama pull "$model" 2>&1; then
        print_status "success" "Pulled $name"
        ((PULLED++))
    else
        print_status "warning" "Could not pull $name (may require Ollama Cloud auth)"
        ((FAILED++))
    fi
    echo ""
done

# Step 5: List available models
echo ""
echo "Step 5: Available models:"
echo "================================"
ollama list
echo "================================"

# Summary
echo ""
echo "Setup Summary:"
echo "─────────────────────────────────"
print_status "success" "Ollama installed and running"
print_status "info" "Models pulled: $PULLED"
if [ $FAILED -gt 0 ]; then
    print_status "warning" "Models failed: $FAILED (may need cloud auth)"
fi

echo ""
echo "Next Steps:"
echo "─────────────────────────────────"
echo "1. Run benchmark:"
echo "   python agents/ollama_benchmark_enhanced.py"
echo ""
echo "2. Compare specific models:"
echo "   python agents/ollama_benchmark_enhanced.py --models kimi-k2.5 glm-5"
echo ""
echo "3. Test with Ollama directly:"
echo "   ollama run kimi-k2.5:cloud \"Write a Python function\""
echo "   ollama run glm5 \"Hello, can you write a Python function to calculate fibonacci?\""
echo ""
echo "For Ollama Cloud models, authenticate with:"
echo "   ollama signin"
echo ""
