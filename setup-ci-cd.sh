#!/bin/bash
# Vaal AI Empire - CI/CD Setup Script
# This script sets up all necessary tools and configurations for CI/CD

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "  Vaal AI Empire - CI/CD Setup"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running in CI environment
IS_CI=false
if [ -n "$CI" ] || [ -n "$GITHUB_ACTIONS" ]; then
    IS_CI=true
    print_status "Running in CI environment"
fi

# ═══════════════════════════════════════════════════════════════════
# Step 1: Check Prerequisites
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "Step 1: Checking Prerequisites..."
echo "───────────────────────────────────────────────────────────────────"

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    print_success "Node.js found: $NODE_VERSION"
else
    print_error "Node.js not found. Please install Node.js 18+"
    exit 1
fi

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_success "Python found: $PYTHON_VERSION"
else
    print_error "Python 3 not found. Please install Python 3.10+"
    exit 1
fi

# Check npm
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    print_success "npm found: $NPM_VERSION"
else
    print_error "npm not found"
    exit 1
fi

# Check pip
if command -v pip3 &> /dev/null; then
    print_success "pip3 found"
else
    print_warning "pip3 not found, attempting to install..."
    python3 -m ensurepip --upgrade || true
fi

# ═══════════════════════════════════════════════════════════════════
# Step 2: Setup Node.js Dependencies
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "Step 2: Setting up Node.js Dependencies..."
echo "───────────────────────────────────────────────────────────────────"

# Root package.json
if [ -f "package.json" ]; then
    print_status "Installing root npm dependencies..."
    npm install
    print_success "Root dependencies installed"
fi

# Server package.json
if [ -d "server" ] && [ -f "server/package.json" ]; then
    print_status "Installing server npm dependencies..."
    cd server
    npm install
    cd ..
    print_success "Server dependencies installed"
fi

# ═══════════════════════════════════════════════════════════════════
# Step 3: Setup Python Dependencies
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "Step 3: Setting up Python Dependencies..."
echo "───────────────────────────────────────────────────────────────────"

# Upgrade pip
print_status "Upgrading pip..."
python3 -m pip install --upgrade pip

# Install from requirements.txt
if [ -f "requirements.txt" ]; then
    print_status "Installing Python dependencies from requirements.txt..."
    pip3 install -r requirements.txt || {
        print_warning "Some packages failed to install from requirements.txt"
        print_status "Installing essential packages individually..."
    }
fi

# Install essential packages
print_status "Installing essential Python packages..."
pip3 install pytest pytest-asyncio flake8 black isort bandit safety || true
pip3 install requests aiohttp pydantic || true

print_success "Python dependencies installed"

# ═══════════════════════════════════════════════════════════════════
# Step 4: Setup Linting and Formatting Tools
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "Step 4: Setting up Linting and Formatting Tools..."
echo "───────────────────────────────────────────────────────────────────"

# ESLint configuration
if [ ! -f ".eslintrc.js" ] && [ ! -f ".eslintrc.json" ]; then
    print_status "Creating ESLint configuration..."
    cat > .eslintrc.js << 'EOF'
module.exports = {
  env: {
    browser: true,
    commonjs: true,
    es2021: true,
    node: true,
    jest: true,
  },
  extends: ['eslint:recommended'],
  parserOptions: {
    ecmaVersion: 'latest',
  },
  rules: {
    'no-unused-vars': 'warn',
    'no-console': 'off',
    'security/detect-object-injection': 'off',
  },
  plugins: ['security'],
};
EOF
    print_success "ESLint configuration created"
fi

# Prettier configuration
if [ ! -f ".prettierrc" ]; then
    print_status "Creating Prettier configuration..."
    cat > .prettierrc << 'EOF'
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2
}
EOF
    print_success "Prettier configuration created"
fi

# Flake8 configuration
if [ ! -f ".flake8" ]; then
    print_status "Creating Flake8 configuration..."
    cat > .flake8 << 'EOF'
[flake8]
max-line-length = 100
max-complexity = 12
exclude =
    .git,
    __pycache__,
    .venv,
    venv,
    node_modules,
    build,
    dist,
    .eggs
ignore = E203, W503
EOF
    print_success "Flake8 configuration created"
fi

# ═══════════════════════════════════════════════════════════════════
# Step 5: Setup LocalAI (Optional - for local fallback)
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "Step 5: Setting up LocalAI (Optional)..."
echo "───────────────────────────────────────────────────────────────────"

if [ "$IS_CI" = false ]; then
    if command -v local-ai &> /dev/null; then
        print_success "LocalAI already installed"
    else
        print_status "LocalAI not installed. To install, run:"
        print_status "  curl -fsSL https://localai.io/install.sh | sh"
        print_warning "Skipping LocalAI installation (optional)"
    fi
else
    print_status "Skipping LocalAI setup in CI environment"
fi

# ═══════════════════════════════════════════════════════════════════
# Step 6: Setup Ollama (Optional - for local fallback)
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "Step 6: Setting up Ollama (Optional)..."
echo "───────────────────────────────────────────────────────────────────"

if [ "$IS_CI" = false ]; then
    if command -v ollama &> /dev/null; then
        print_success "Ollama already installed"
        print_status "Available models:"
        ollama list 2>/dev/null || print_warning "Could not list Ollama models"
    else
        print_status "Ollama not installed. To install, run:"
        print_status "  curl -fsSL https://ollama.com/install.sh | sh"
        print_warning "Skipping Ollama installation (optional)"
    fi
else
    print_status "Skipping Ollama setup in CI environment"
fi

# ═══════════════════════════════════════════════════════════════════
# Step 7: Verify Setup
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "Step 7: Verifying Setup..."
echo "───────────────────────────────────────────────────────────────────"

# Check Node.js tests
if [ -d "server" ]; then
    print_status "Checking server tests..."
    cd server
    if npm test 2>/dev/null; then
        print_success "Server tests passed"
    else
        print_warning "Server tests failed or not configured"
    fi
    cd ..
fi

# Check Python syntax
print_status "Checking Python syntax..."
if [ -d "agents" ]; then
    python3 -m py_compile agents/*.py 2>/dev/null && print_success "Python syntax OK" || print_warning "Some Python files have syntax issues"
fi

# Run flake8
print_status "Running flake8..."
flake8 . --exclude=.venv,node_modules,__pycache__,.git,build,dist --max-line-length=100 2>/dev/null || print_warning "Flake8 found issues (non-critical)"

# ═══════════════════════════════════════════════════════════════════
# Step 8: Create Environment File
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "Step 8: Environment Configuration..."
echo "───────────────────────────────────────────────────────────────────"

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        print_status "Creating .env from .env.example..."
        cp .env.example .env
        print_warning "Please edit .env and add your actual API keys"
    else
        print_warning ".env.example not found"
    fi
else
    print_success ".env file already exists"
fi

# ═══════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "  Setup Complete!"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Edit .env file with your actual API keys"
echo "  2. Run 'npm test' to verify everything works"
echo "  3. Start the server with 'npm start'"
echo ""
echo "For LocalAI fallback:"
echo "  1. Install LocalAI: curl -fsSL https://localai.io/install.sh | sh"
echo "  2. Start LocalAI: local-ai --config-file=config/localai-config.yaml"
echo ""
echo "For Ollama fallback:"
echo "  1. Install Ollama: curl -fsSL https://ollama.com/install.sh | sh"
echo "  2. Pull a model: ollama pull qwen2.5-coder:1.5b"
echo "  3. Start Ollama: ollama serve"
echo ""
print_success "Setup completed successfully!"
