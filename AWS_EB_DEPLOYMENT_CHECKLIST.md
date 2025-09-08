# AWS Elastic Beanstalk Deployment Checklist

## Pre-Deployment Requirements

### ✅ AWS Setup
- [ ] AWS CLI installed and configured
- [ ] EB CLI installed (`pip install awsebcli`)
- [ ] AWS account with appropriate permissions
- [ ] RDS PostgreSQL instance created
- [ ] S3 bucket created for asset storage
- [ ] IAM roles configured for EB

### ✅ Database Setup
- [ ] PostgreSQL RDS instance running
- [ ] Database `whatsapp_server` created
- [ ] Database user with appropriate permissions
- [ ] Network security groups configured
- [ ] Database migration script ready

### ✅ Application Setup
- [ ] Repository cloned locally
- [ ] `.env` file configured with RDS and S3 settings
- [ ] All dependencies listed in `requirements.txt`
- [ ] EB configuration files in `.ebextensions/`

## Deployment Steps

### Step 1: Initialize EB Application
```bash
# Navigate to project directory
cd whatsapp-assids-generate-server

# Initialize EB application
eb init whatsapp-asset-server --platform python-3.11 --region us-east-1
```

### Step 2: Create Environment
```bash
# Create production environment
eb create production --instance-type t3.medium --min-instances 1 --max-instances 5

# Or create staging environment
eb create staging --instance-type t3.small --min-instances 1 --max-instances 2
```

### Step 3: Configure Environment Variables
```bash
# Database configuration
eb setenv DATABASE_URL="postgresql://username:password@your-rds-endpoint:5432/whatsapp_server"

# AWS credentials
eb setenv AWS_ACCESS_KEY_ID="your-access-key-id"
eb setenv AWS_SECRET_ACCESS_KEY="your-secret-access-key"
eb setenv AWS_REGION="us-east-1"

# S3 configuration
eb setenv S3_BUCKET_NAME="your-s3-bucket-name"

# Application settings
eb setenv DEBUG="False"
eb setenv LOG_LEVEL="INFO"
eb setenv CRON_ENABLED="True"
eb setenv MAX_CONCURRENT_GENERATIONS="10"
eb setenv ASSET_TEMP_DIR="/var/app/current/temp_assets"
```

### Step 4: Deploy Application
```bash
# Deploy to EB
eb deploy

# Check deployment status
eb status
eb health
```

### Step 5: Apply Database Migration
```bash
# Connect to RDS and apply migration
psql -h your-rds-endpoint -U your-username -d whatsapp_server -f migrations/add_asset_generation_tables.sql
```

### Step 6: Verify Deployment
```bash
# Check application health
eb health

# View application logs
eb logs

# Test health endpoint
curl https://your-eb-environment-url/health

# Test API documentation
curl https://your-eb-environment-url/docs
```

## Post-Deployment Verification

### ✅ Health Checks
- [ ] Application health endpoint responding
- [ ] Database connection working
- [ ] S3 integration functional
- [ ] Cron scheduler running
- [ ] API endpoints accessible

### ✅ Monitoring Setup
- [ ] CloudWatch logs configured
- [ ] CloudWatch metrics enabled
- [ ] Auto-scaling policies configured
- [ ] Health monitoring alerts set up

### ✅ Testing
- [ ] Create test campaign in database
- [ ] Verify asset generation works
- [ ] Check S3 uploads
- [ ] Test recovery mechanisms
- [ ] Verify monitoring dashboard

## Maintenance Commands

### Regular Operations
```bash
# Check application status
eb status

# View real-time health
eb health --refresh

# View logs
eb logs

# Deploy updates
eb deploy

# Scale environment
eb scale 3

# Update environment variables
eb setenv NEW_VAR="new_value"
```

### Troubleshooting
```bash
# SSH into instance
eb ssh

# Check detailed logs
eb logs --all

# View environment configuration
eb config

# List environment variables
eb printenv

# Restart application
eb deploy --staged
```

## Security Considerations

### ✅ Security Checklist
- [ ] Database security groups restrict access
- [ ] S3 bucket has appropriate permissions
- [ ] Environment variables contain no sensitive data in plain text
- [ ] HTTPS enabled for production
- [ ] IAM roles follow least privilege principle
- [ ] Application logs don't contain sensitive information

## Scaling Configuration

### Auto Scaling Settings
```bash
# Configure auto-scaling
eb config

# Set scaling triggers:
# - CPU utilization > 70% for 5 minutes: scale up
# - CPU utilization < 30% for 10 minutes: scale down
# - Min instances: 1
# - Max instances: 5
```

### Performance Optimization
- [ ] Instance type appropriate for workload
- [ ] Database connection pooling configured
- [ ] S3 upload optimization enabled
- [ ] Caching strategies implemented
- [ ] Log rotation configured

## Backup and Recovery

### ✅ Backup Strategy
- [ ] RDS automated backups enabled
- [ ] S3 bucket versioning enabled
- [ ] Application code in version control
- [ ] Environment configuration documented
- [ ] Recovery procedures tested

## Cost Optimization

### ✅ Cost Management
- [ ] Right-sized instance types
- [ ] Auto-scaling configured to minimize costs
- [ ] Unused resources cleaned up
- [ ] CloudWatch billing alerts set up
- [ ] Reserved instances considered for production

---

## Quick Reference

### Environment URLs
- **Production**: `https://production.your-region.elasticbeanstalk.com`
- **Staging**: `https://staging.your-region.elasticbeanstalk.com`

### Key Endpoints
- Health Check: `/health`
- API Documentation: `/docs`
- Monitoring Dashboard: `/api/v1/monitoring/dashboard`
- Recovery Statistics: `/api/v1/recovery/statistics`

### Support Contacts
- AWS Support: [Your AWS Support Plan]
- Development Team: [Your Team Contact]
- Database Admin: [DBA Contact]
