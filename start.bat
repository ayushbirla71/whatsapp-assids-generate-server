@echo off
REM WhatsApp Asset Generation Server Startup Script for Windows

echo 🚀 Starting WhatsApp Asset Generation Server...

REM Check if .env file exists
if not exist .env (
    echo ❌ .env file not found. Please copy .env.example to .env and configure it.
    pause
    exit /b 1
)

REM Create necessary directories
echo 📁 Creating directories...
if not exist logs mkdir logs
if not exist temp_assets mkdir temp_assets

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.11 or higher.
    pause
    exit /b 1
)

REM Install dependencies
echo 📦 Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies.
    pause
    exit /b 1
)

REM Run setup test
echo 🧪 Running setup tests...
python test_setup.py
if errorlevel 1 (
    echo ❌ Setup tests failed. Please check your configuration.
    pause
    exit /b 1
)

echo ✅ Setup tests passed!

REM Start the server
echo 🌟 Starting the asset generation server...
python main.py

pause
