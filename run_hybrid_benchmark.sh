#!/bin/bash
# Vaal AI Empire - Hybrid Benchmark Runner
# Runs benchmarks with automatic backend selection
#
# Usage:
#   ./run_hybrid_benchmark.sh [auto|ollama|direct] [category]
#
# Examples:
#   ./run_hybrid_benchmark.sh auto            # Auto-detect best backend
#   ./run_hybrid_benchmark.sh ollama          # Force Ollama mode
#   ./run_hybrid_benchmark.sh direct security # Direct API, security tests only

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
BACKEND="${1:-auto}"
CATEGORY="${2:-}"
OUTPUT="benchmark_results/report_$(date +%Y%m%d_%H%M%S).json"

# Print banner
echo -e "${BLUE}"
echo "============================================================"
echo "  VAAL AI EMPIRE - HYBRID BENCHMARK RUNNER"
echo "============================================================"
echo -e "${NC}"

echo -e "Backend Mode: ${GREEN}${BACKEND}${NC}"
if [ -n "$CATEGORY" ]; then
    echo -e "Category: ${GREEN}${CATEGORY}${NC}"
fi
echo ""

# Function to check Ollama availability
check_ollama() {
    if command -v ollama &> /dev/null; then
        if ollama list &> /dev/null; then
            return 0
        else
            echo -e "${YELLOW}⚠️  Ollama is installed but not running${NC}"
            echo "   Starting Ollama daemon..."
            ollama serve &
            sleep 3
            return 0
        fi
    else
        return 1
    fi
}

# Function to check Direct API availability
check_direct_api() {
    local available=""
    
    if [ -n "$KIMI_API_KEY" ]; then
        available="${available}kimi "
    fi
    
    if [ -n "$GLM5_API_KEY" ]; then
        available="${available}glm "
    fi
    
    if [ -n "$DASHSCOPE_API_KEY" ]; then
        available="${available}dashscope "
    fi
    
    echo "$available"
}

# Show backend availability
echo -e "${BLUE}Checking backend availability...${NC}"
echo ""

# Check Ollama
if check_ollama; then
    echo -e "  ${GREEN}✅${NC} Ollama: Available"
    echo -e "     Models: $(ollama list 2>/dev/null | tail -n +2 | head -5 | awk '{print $1}' | tr '\n' ' ')"
else
    echo -e "  ${RED}❌${NC} Ollama: Not installed"
    echo -e "     Install: curl -fsSL https://ollama.com/install.sh | sh"
fi

# Check Direct API
DIRECT_AVAILABLE=$(check_direct_api)
if [ -n "$DIRECT_AVAILABLE" ]; then
    echo -e "  ${GREEN}✅${NC} Direct API: $DIRECT_AVAILABLE"
else
    echo -e "  ${YELLOW}⚠️${NC}  Direct API: No API keys configured"
    echo -e "     Set environment variables: KIMI_API_KEY, GLM5_API_KEY, DASHSCOPE_API_KEY"
fi

echo ""

# Auto mode logic
if [ "$BACKEND" = "auto" ]; then
    if check_ollama; then
        echo -e "${GREEN}Auto mode: Using Ollama backend${NC}"
        BACKEND="ollama"
    elif [ -n "$DIRECT_AVAILABLE" ]; then
        echo -e "${GREEN}Auto mode: Using Direct API backend${NC}"
        BACKEND="direct"
    else
        echo -e "${YELLOW}Auto mode: No backend available, running in resilient mode${NC}"
        BACKEND="auto"
    fi
    echo ""
fi

# Create output directory
mkdir -p "$(dirname "$OUTPUT")"

# Build command
CMD="python3 agents/benchmark_executor.py --run-all --report --backend $BACKEND --output $OUTPUT"

if [ -n "$CATEGORY" ]; then
    CMD="$CMD --category $CATEGORY"
fi

# Run benchmark
echo -e "${BLUE}Running benchmark...${NC}"
echo -e "Command: $CMD"
echo ""

eval $CMD

# Show results
echo ""
echo -e "${BLUE}============================================================${NC}"
echo -e "${GREEN}✅ Benchmark complete!${NC}"
echo -e "Report saved to: ${OUTPUT}"
echo -e "${BLUE}============================================================${NC}"

# Optional: Open report
if command -v jq &> /dev/null; then
    echo ""
    echo -e "${BLUE}Quick Summary:${NC}"
    jq '.summary' "$OUTPUT" 2>/dev/null || echo "Could not parse report"
fi
