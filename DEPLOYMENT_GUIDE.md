# WhatsApp Asset Generation Server - Deployment Guide

## 🚀 Complete Fault-Tolerant Asset Generation System

This guide will help you deploy a robust, fault-tolerant asset generation server on AWS Elastic Beanstalk that handles everything from server crashes to stuck processes automatically.

## ✅ What You Get

### Core Features

- **Automated Asset Generation**: Cron job monitors campaigns every minute
- **Fault Tolerance**: Automatic recovery from crashes, stuck processes, and failures
- **Retry Logic**: Intelligent retry mechanism with exponential backoff
- **Progress Tracking**: Real-time progress monitoring for campaigns
- **S3 Integration**: Automatic upload of generated assets
- **Comprehensive Monitoring**: System health, performance metrics, and error tracking
- **RESTful API**: Complete API for monitoring and management
- **AWS Elastic Beanstalk Ready**: Optimized for AWS EB deployment

### Fault Tolerance Features

- ✅ **Server Crash Recovery**: Automatically resumes incomplete campaigns on restart
- ✅ **Stuck Process Detection**: Detects and recovers processes stuck for >30 minutes
- ✅ **Retry Mechanism**: Up to 3 retries for failed asset generations
- ✅ **Progress Checkpoints**: Resume from last successful checkpoint
- ✅ **Database Reconnection**: Handles database connection losses
- ✅ **S3 Upload Retries**: Retries failed S3 uploads with backoff
- ✅ **Memory/CPU Monitoring**: Monitors system resources
- ✅ **Error Tracking**: Detailed error logging and reporting
- ✅ **Auto-Scaling**: Scales with AWS Elastic Beanstalk auto-scaling

## 📋 Pre-Deployment Checklist

### 1. Database Setup

- [ ] PostgreSQL database running
- [ ] Existing WhatsApp server schema in place
- [ ] Database user with appropriate permissions

### 2. AWS S3 Setup

- [ ] S3 bucket created
- [ ] AWS credentials with S3 access
- [ ] Bucket permissions configured

### 3. Environment Configuration

- [ ] `.env` file configured with all required variables
- [ ] Network connectivity to database and S3
- [ ] Sufficient disk space for temporary assets

## 🛠️ Deployment Options

### Option 1: AWS Elastic Beanstalk (Recommended for Production)

#### Prerequisites

- AWS CLI installed and configured
- EB CLI installed (`pip install awsebcli`)
- PostgreSQL RDS instance (recommended)
- S3 bucket for assets

#### Step 1: Prepare Application

```bash
git clone <repository-url>
cd whatsapp-assids-generate-server
cp .env.example .env
# Edit .env with your AWS RDS and S3 configuration
```

#### Step 2: Create Elastic Beanstalk Application

```bash
# Initialize EB application
eb init whatsapp-asset-server --platform python-3.11 --region us-east-1

# Create environment
eb create production --instance-type t3.medium --min-instances 1 --max-instances 5
```

#### Step 3: Configure Environment Variables

```bash
# Set environment variables in EB
eb setenv DATABASE_URL="postgresql://user:pass@your-rds-endpoint:5432/whatsapp_server"
eb setenv AWS_ACCESS_KEY_ID="your-access-key"
eb setenv AWS_SECRET_ACCESS_KEY="your-secret-key"
eb setenv AWS_REGION="us-east-1"
eb setenv S3_BUCKET_NAME="your-bucket-name"
eb setenv DEBUG="False"
eb setenv LOG_LEVEL="INFO"
eb setenv CRON_ENABLED="True"
eb setenv MAX_CONCURRENT_GENERATIONS="10"
```

#### Step 4: Deploy Application

```bash
# Deploy to Elastic Beanstalk
eb deploy

# Check status
eb status
eb health
```

#### Step 5: Apply Database Migration

```bash
# Connect to your RDS instance and run:
psql -h your-rds-endpoint -U your-user -d whatsapp_server -f migrations/add_asset_generation_tables.sql
```

### Option 2: Local Development/Testing

1. **Setup Environment**

   ```bash
   git clone <repository-url>
   cd whatsapp-assids-generate-server
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Apply Database Migration**

   ```bash
   # Windows (if PostgreSQL installed locally)
   "C:\Program Files\PostgreSQL\17\bin\psql.exe" -h localhost -U postgres -d whatsapp_server -f migrations\add_asset_generation_tables.sql

   # Linux/Mac
   psql -h localhost -U postgres -d whatsapp_server -f migrations/add_asset_generation_tables.sql
   ```

4. **Start Server**

   ```bash
   # Windows
   .\start.ps1
   # or
   python main.py

   # Linux/Mac
   ./start.sh
   # or
   python main.py
   ```

## 📊 Monitoring & Management

### Real-time Dashboard

```bash
# Install dashboard dependencies
pip install aiohttp

# Run interactive dashboard
python dashboard.py

# Single status check
python dashboard.py --once
```

### API Endpoints for Monitoring

```bash
# System health check
curl http://localhost:8000/api/v1/health/detailed

# Check stuck processes
curl http://localhost:8000/api/v1/monitoring/stuck-processes

# Get recovery statistics
curl http://localhost:8000/api/v1/recovery/statistics

# Manual recovery triggers
curl -X POST http://localhost:8000/api/v1/recovery/startup
curl -X POST http://localhost:8000/api/v1/recovery/runtime
```

### Campaign Status Monitoring

```bash
# Get campaign status
curl http://localhost:8000/api/v1/campaigns/{campaign-id}/status

# Get campaigns by status
curl http://localhost:8000/api/v1/campaigns/status/asset_generation

# Get audience members with status
curl http://localhost:8000/api/v1/campaigns/{campaign-id}/audience
```

## 🔧 Configuration

### Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:pass@host:5432/whatsapp_server

# AWS S3
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket

# Application
DEBUG=False
LOG_LEVEL=INFO
CRON_ENABLED=True
ASSET_TEMP_DIR=./temp_assets
MAX_CONCURRENT_GENERATIONS=5
```

### Asset Generation Files

Create asset generation files in the database:

```sql
INSERT INTO asset_generate_files (template_id, file_name, file_content, description)
VALUES (
    'your-template-id',
    'my_asset_generator.py',
    'your-python-code-here',
    'Description of what this generates'
);
```

## 🚨 Troubleshooting

### Common Issues

1. **Server Won't Start**

   ```bash
   # Check configuration
   python test_setup.py

   # Check logs
   tail -f logs/asset_generator.log
   ```

2. **Asset Generation Stuck**

   ```bash
   # Check stuck processes
   curl http://localhost:8000/api/v1/monitoring/stuck-processes

   # Trigger recovery
   curl -X POST http://localhost:8000/api/v1/recovery/runtime
   ```

3. **Database Connection Issues**

   ```bash
   # Test database connectivity
   python -c "
   import asyncio
   from database import AsyncSessionLocal
   async def test():
       async with AsyncSessionLocal() as session:
           await session.execute('SELECT 1')
       print('Database OK')
   asyncio.run(test())
   "
   ```

4. **S3 Upload Failures**
   ```bash
   # Test S3 connectivity
   python -c "
   from s3_uploader import S3Uploader
   uploader = S3Uploader()
   print('S3 client:', 'OK' if uploader.s3_client else 'Failed')
   "
   ```

### Recovery Scenarios

The system automatically handles:

- Server crashes and restarts
- Stuck asset generation processes
- Failed S3 uploads
- Database connection losses
- Memory/CPU resource issues

### Manual Recovery

If automatic recovery fails:

```bash
# Force startup recovery
curl -X POST http://localhost:8000/api/v1/recovery/startup

# Check what's stuck
curl http://localhost:8000/api/v1/monitoring/stuck-processes

# Update campaign status manually
curl -X PUT http://localhost:8000/api/v1/campaigns/{id}/status \
  -H "Content-Type: application/json" \
  -d '{"status": "approved"}'
```

## 📈 Performance Tuning

### Optimize for High Volume

```env
# Increase concurrent generations
MAX_CONCURRENT_GENERATIONS=10

# Adjust batch sizes in code
# Edit asset_generator.py batch_size settings
```

### Monitor Performance

```bash
# Use the dashboard for real-time monitoring
python dashboard.py

# Check performance metrics
curl http://localhost:8000/api/v1/health/detailed | jq '.performance_metrics'
```

## 🔒 Security Considerations

1. **Database Security**: Use strong passwords and limit database access
2. **S3 Security**: Use IAM roles with minimal required permissions
3. **API Security**: Consider adding authentication for production
4. **Network Security**: Use HTTPS in production
5. **Log Security**: Ensure logs don't contain sensitive information

## 📞 Support

For issues or questions:

1. Check the logs in `logs/` directory
2. Run the test script: `python test_setup.py`
3. Use the monitoring dashboard: `python dashboard.py`
4. Check the API health endpoint: `/api/v1/health/detailed`

## 🎯 Next Steps

After deployment:

1. Create your asset generation files in the database
2. Test with a small campaign first
3. Monitor the dashboard for any issues
4. Scale up gradually based on performance metrics

The system is designed to handle everything automatically, but monitoring is recommended for optimal performance.
