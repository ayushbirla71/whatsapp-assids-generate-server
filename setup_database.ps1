# Database Setup Script for Windows PowerShell

param(
    [string]$Host = "localhost",
    [string]$Port = "5432",
    [string]$Username = "postgres",
    [string]$Database = "whatsapp_server",
    [string]$Password = ""
)

Write-Host "🗄️ Setting up WhatsApp Asset Generation Database..." -ForegroundColor Green

# Function to find PostgreSQL installation
function Find-PostgreSQL {
    $possiblePaths = @(
        "C:\Program Files\PostgreSQL\*\bin\psql.exe",
        "C:\Program Files (x86)\PostgreSQL\*\bin\psql.exe",
        "C:\PostgreSQL\*\bin\psql.exe"
    )
    
    foreach ($path in $possiblePaths) {
        $found = Get-ChildItem -Path $path -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) {
            return $found.FullName
        }
    }
    return $null
}

# Try to find psql
$psqlPath = Find-PostgreSQL

if (-not $psqlPath) {
    Write-Host "❌ PostgreSQL psql command not found!" -ForegroundColor Red
    Write-Host "Please ensure PostgreSQL is installed and try one of these options:" -ForegroundColor Yellow
    Write-Host "1. Add PostgreSQL bin directory to your PATH" -ForegroundColor White
    Write-Host "2. Use pgAdmin to run the migration script manually" -ForegroundColor White
    Write-Host "3. Specify the full path to psql.exe" -ForegroundColor White
    Write-Host ""
    Write-Host "Migration file location: migrations\add_asset_generation_tables.sql" -ForegroundColor Cyan
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✅ Found PostgreSQL at: $psqlPath" -ForegroundColor Green

# Check if migration file exists
if (-not (Test-Path "migrations\add_asset_generation_tables.sql")) {
    Write-Host "❌ Migration file not found: migrations\add_asset_generation_tables.sql" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Prompt for password if not provided
if (-not $Password) {
    $securePassword = Read-Host "Enter PostgreSQL password for user '$Username'" -AsSecureString
    $Password = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword))
}

# Set environment variable for password
$env:PGPASSWORD = $Password

Write-Host "🔗 Connecting to database..." -ForegroundColor Yellow
Write-Host "Host: $Host" -ForegroundColor White
Write-Host "Port: $Port" -ForegroundColor White
Write-Host "Database: $Database" -ForegroundColor White
Write-Host "Username: $Username" -ForegroundColor White

try {
    # Test connection first
    Write-Host "Testing database connection..." -ForegroundColor Yellow
    & $psqlPath -h $Host -p $Port -U $Username -d $Database -c "SELECT 1;" 2>&1 | Out-Null
    
    if ($LASTEXITCODE -ne 0) {
        throw "Connection test failed"
    }
    
    Write-Host "✅ Database connection successful" -ForegroundColor Green
    
    # Run the migration
    Write-Host "📋 Applying database migration..." -ForegroundColor Yellow
    & $psqlPath -h $Host -p $Port -U $Username -d $Database -f "migrations\add_asset_generation_tables.sql"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Database migration completed successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "🎉 Database setup complete! You can now start the asset generation server." -ForegroundColor Green
    } else {
        throw "Migration failed"
    }
    
} catch {
    Write-Host "❌ Database setup failed: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting tips:" -ForegroundColor Yellow
    Write-Host "1. Verify database connection details" -ForegroundColor White
    Write-Host "2. Ensure the database '$Database' exists" -ForegroundColor White
    Write-Host "3. Check user '$Username' has sufficient permissions" -ForegroundColor White
    Write-Host "4. Verify PostgreSQL service is running" -ForegroundColor White
    Write-Host ""
    Write-Host "You can also run the migration manually using pgAdmin:" -ForegroundColor Cyan
    Write-Host "File: migrations\add_asset_generation_tables.sql" -ForegroundColor Cyan
} finally {
    # Clear password from environment
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}

Read-Host "Press Enter to exit"
