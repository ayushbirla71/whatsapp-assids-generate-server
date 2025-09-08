# Windows Setup Guide - WhatsApp Asset Generation Server

## 🚀 Quick Setup for Windows

### Step 1: Configure Environment
```powershell
# Copy the example environment file
Copy-Item .env.example .env

# Edit .env file with your configuration
notepad .env
```

### Step 2: Setup Database
```powershell
# Option A: Use the automated script
.\setup_database.ps1

# Option B: Manual setup with custom parameters
.\setup_database.ps1 -Host "your-db-host" -Username "your-user" -Database "whatsapp_server"

# Option C: If psql is not found, use pgAdmin
# 1. Open pgAdmin
# 2. Connect to your database
# 3. Open Query Tool
# 4. Copy contents of migrations\add_asset_generation_tables.sql
# 5. Execute the script
```

### Step 3: Start the Server
```powershell
# Use the PowerShell script
.\start.ps1

# OR use the batch file
.\start.bat
```

## 🔧 Troubleshooting

### PostgreSQL Issues

**Problem**: `psql` command not found
```powershell
# Solution 1: Find PostgreSQL installation
Get-ChildItem -Path "C:\Program Files\PostgreSQL" -Recurse -Name "psql.exe"

# Solution 2: Add to PATH temporarily
$env:PATH += ";C:\Program Files\PostgreSQL\15\bin"

# Solution 3: Use full path
"C:\Program Files\PostgreSQL\15\bin\psql.exe" -h localhost -U postgres -d whatsapp_server -f migrations\add_asset_generation_tables.sql
```

**Problem**: Connection refused
- Check if PostgreSQL service is running
- Verify connection details in .env file
- Check firewall settings

### Python Issues

**Problem**: Python not found
```powershell
# Check if Python is installed
python --version

# If not installed, download from python.org
# Make sure to check "Add Python to PATH" during installation
```

**Problem**: Permission errors
```powershell
# Run PowerShell as Administrator
# OR use virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### PowerShell Execution Policy

If you get execution policy errors:
```powershell
# Check current policy
Get-ExecutionPolicy

# Set policy for current user (recommended)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# OR bypass for single script
PowerShell -ExecutionPolicy Bypass -File .\start.ps1
```

## 📊 Monitoring

### Start the Dashboard
```powershell
# Install dashboard dependencies
pip install aiohttp

# Run the monitoring dashboard
python dashboard.py

# Single status check
python dashboard.py --once
```

### Check System Health
```powershell
# Using curl (if installed)
curl http://localhost:8000/api/v1/health/detailed

# Using PowerShell (built-in)
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health/detailed" -Method Get
```

## 🐳 Docker Alternative

If you prefer Docker:
```powershell
# Make sure Docker Desktop is installed and running
docker --version

# Start with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 📝 Configuration Examples

### .env file example for Windows
```env
# Database Configuration
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/whatsapp_server

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name

# Application Configuration
DEBUG=True
LOG_LEVEL=INFO
CRON_ENABLED=True

# Asset Generation Configuration
ASSET_TEMP_DIR=./temp_assets
MAX_CONCURRENT_GENERATIONS=5
```

## 🔍 Verification Steps

### 1. Test Database Connection
```powershell
python -c "
import asyncio
import sys
sys.path.append('.')
from database import AsyncSessionLocal

async def test():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute('SELECT 1')
        print('✅ Database connection successful')
    except Exception as e:
        print(f'❌ Database connection failed: {e}')

asyncio.run(test())
"
```

### 2. Test S3 Connection
```powershell
python -c "
import sys
sys.path.append('.')
from s3_uploader import S3Uploader

try:
    uploader = S3Uploader()
    if uploader.s3_client:
        print('✅ S3 connection successful')
    else:
        print('❌ S3 connection failed')
except Exception as e:
    print(f'❌ S3 error: {e}')
"
```

### 3. Run Full Setup Test
```powershell
python test_setup.py
```

## 🎯 Next Steps

After successful setup:

1. **Create Asset Generation Files**: Add your Python asset generation code to the database
2. **Test with Sample Campaign**: Create a test campaign to verify everything works
3. **Monitor Performance**: Use the dashboard to monitor system performance
4. **Scale as Needed**: Adjust `MAX_CONCURRENT_GENERATIONS` based on your requirements

## 📞 Common Commands Reference

```powershell
# Start server
.\start.ps1

# Setup database
.\setup_database.ps1

# Run tests
python test_setup.py

# Monitor system
python dashboard.py

# Check health
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get

# View logs
Get-Content logs\asset_generator.log -Tail 50 -Wait
```
