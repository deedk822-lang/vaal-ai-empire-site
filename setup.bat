@echo off
REM Vaal AI Empire - Windows Setup Script
REM Run this script on Windows to install everything

echo.
echo ⚡ Vaal AI Empire - Stripe Setup Installer
echo ==========================================
echo.

REM Check if Node.js is installed
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Node.js is not installed!
    echo Please install Node.js 18+ from: https://nodejs.org/
    pause
    exit /b 1
)

echo ✅ Node.js installed
node --version

REM Check if npm is installed
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ npm is not installed!
    pause
    exit /b 1
)

echo ✅ npm installed
npm --version
echo.

REM Navigate to server directory
if not exist "server" (
    echo ❌ Server directory not found!
    echo Make sure you're in the vaal-ai-empire-site root directory.
    pause
    exit /b 1
)

cd server

echo 📦 Installing Node.js dependencies...
call npm install

if %errorlevel% equ 0 (
    echo ✅ Dependencies installed successfully!
) else (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

echo.

REM Create .env file if it doesn't exist
if not exist ".env" (
    echo 📄 Creating .env file from template...
    copy .env.example .env
    echo ✅ .env file created
    echo.
    echo ⚠️  IMPORTANT: Edit server\.env and add your Stripe keys!
    echo    1. Go to: https://dashboard.stripe.com/test/apikeys
    echo    2. Copy your Publishable key (pk_test_...)
    echo    3. Copy your Secret key (sk_test_...)
    echo    4. Update server\.env with these values
    echo.
) else (
    echo ✅ .env file already exists
)

echo.
echo ✅ Setup Complete!
echo.
echo Next steps:
echo 1. Edit server\.env with your Stripe API keys
echo 2. Create products in Stripe Dashboard
echo 3. Add price IDs to server\.env
echo 4. Run: npm start
echo 5. Visit: http://localhost:4242/pricing
echo.
echo Full guide: See STRIPE_SETUP.md
echo.
echo ⚡ Built in the Vaal. Built for Africa.
echo.
pause