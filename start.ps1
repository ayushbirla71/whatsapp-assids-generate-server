# WhatsApp Asset Generation Server Startup Script for PowerShell

Write-Host "🚀 Starting WhatsApp Asset Generation Server..." -ForegroundColor Green

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "❌ .env file not found. Please copy .env.example to .env and configure it." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Create necessary directories
Write-Host "📁 Creating directories..." -ForegroundColor Yellow
if (-not (Test-Path "logs")) { New-Item -ItemType Directory -Name "logs" }
if (-not (Test-Path "temp_assets")) { New-Item -ItemType Directory -Name "temp_assets" }

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python is not installed. Please install Python 3.11 or higher." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if pip is installed
try {
    $pipVersion = pip --version 2>&1
    Write-Host "✅ pip found: $pipVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ pip is not installed. Please install pip." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if dependencies are already installed
Write-Host "📦 Checking Python dependencies..." -ForegroundColor Yellow
try {
    # Check if FastAPI is installed (main dependency)
    python -c "import fastapi; print('FastAPI version:', fastapi.__version__)" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Dependencies already installed" -ForegroundColor Green
    } else {
        Write-Host "📦 Installing Python dependencies..." -ForegroundColor Yellow
        pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            throw "pip install failed"
        }
        Write-Host "✅ Dependencies installed successfully" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Failed to install dependencies: $_" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Run setup test
Write-Host "🧪 Running setup tests..." -ForegroundColor Yellow
try {
    python test_setup.py
    if ($LASTEXITCODE -ne 0) {
        throw "Setup tests failed"
    }
    Write-Host "✅ Setup tests passed!" -ForegroundColor Green
} catch {
    Write-Host "❌ Setup tests failed. Please check your configuration." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Start the server
Write-Host "🌟 Starting the asset generation server..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
try {
    python main.py
} catch {
    Write-Host "❌ Server failed to start: $_" -ForegroundColor Red
}

Read-Host "Press Enter to exit"
