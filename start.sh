#!/bin/bash

# WhatsApp Asset Generation Server Startup Script

set -e

echo "🚀 Starting WhatsApp Asset Generation Server..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please copy .env.example to .env and configure it."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p temp_assets

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi

# Check if pip is installed
if ! command -v pip &> /dev/null; then
    echo "❌ pip is not installed. Please install pip."
    exit 1
fi

# Install dependencies if requirements.txt is newer than last install
if [ requirements.txt -nt .last_install ] || [ ! -f .last_install ]; then
    echo "📦 Installing Python dependencies..."
    pip install -r requirements.txt
    touch .last_install
else
    echo "✅ Dependencies are up to date"
fi

# Run setup test
echo "🧪 Running setup tests..."
python test_setup.py

if [ $? -ne 0 ]; then
    echo "❌ Setup tests failed. Please check your configuration."
    exit 1
fi

echo "✅ Setup tests passed!"

# Start the server
echo "🌟 Starting the asset generation server..."
python main.py
