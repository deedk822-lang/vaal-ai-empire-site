#!/bin/bash
# Vaal AI Empire - Complete Stripe Setup Script
# Run this script to install everything needed for Stripe checkout

set -e  # Exit on error

echo "⚡ Vaal AI Empire - Stripe Setup Installer"
echo "=========================================="
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed!"
    echo "Please install Node.js 18+ from: https://nodejs.org/"
    exit 1
fi

echo "✅ Node.js version: $(node --version)"

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed!"
    exit 1
fi

echo "✅ npm version: $(npm --version)"
echo ""

# Navigate to server directory
if [ ! -d "server" ]; then
    echo "❌ Server directory not found!"
    echo "Make sure you're in the vaal-ai-empire-site root directory."
    exit 1
fi

cd server

echo "📦 Installing Node.js dependencies..."
npm install

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully!"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo ""

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📄 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit server/.env and add your Stripe keys!"
    echo "   1. Go to: https://dashboard.stripe.com/test/apikeys"
    echo "   2. Copy your Publishable key (pk_test_...)"
    echo "   3. Copy your Secret key (sk_test_...)"
    echo "   4. Update server/.env with these values"
    echo ""
else
    echo "✅ .env file already exists"
fi

echo ""
echo "✅ Setup Complete!"
echo ""
echo "Next steps:"
echo "1. Edit server/.env with your Stripe API keys"
echo "2. Create products in Stripe Dashboard"
echo "3. Add price IDs to server/.env"
echo "4. Run: npm start"
echo "5. Visit: http://localhost:4242/pricing"
echo ""
echo "Full guide: See STRIPE_SETUP.md"
echo ""
echo "⚡ Built in the Vaal. Built for Africa."