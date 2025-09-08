# WhatsApp Asset Generation Server

A Python-based server for automatically generating personalized assets (images, videos, documents) for WhatsApp marketing campaigns. This server runs as a background service with a cron job that monitors approved campaigns and generates customized content for each audience member.

## Features

- **Automated Asset Generation**: Cron job runs every minute to check for approved campaigns
- **Dynamic Code Execution**: Loads asset generation code from database and executes it safely
- **S3 Integration**: Automatically uploads generated assets to AWS S3
- **Status Tracking**: Comprehensive status management for campaigns and audience members
- **RESTful API**: Monitor and manage asset generation processes
- **Comprehensive Logging**: Structured logging with JSON format support
- **AWS Elastic Beanstalk Ready**: Optimized for AWS EB deployment with auto-scaling
- **Fault Tolerance**: Automatic recovery from server crashes and stuck processes
- **Retry Mechanism**: Intelligent retry logic for failed asset generations
- **Real-time Monitoring**: System health monitoring and performance metrics
- **Progress Tracking**: Detailed progress tracking for campaigns and individual assets
- **Error Handling**: Comprehensive error handling with detailed error reporting

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Cron Job      │    │  Asset Generator │    │   S3 Uploader   │
│  (Every Minute) │───▶│     Engine       │───▶│                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                       │
         ▼                        ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │  Dynamic Code    │    │   AWS S3        │
│   Database      │    │   Execution      │    │   Storage       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL database (with existing WhatsApp server schema)
- AWS S3 bucket and credentials
- For production: AWS Elastic Beanstalk CLI (`pip install awsebcli`)

### Local Setup

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd whatsapp-assids-generate-server
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run database migrations**

   ```bash
   # Apply the migration script to your existing database
   psql -h localhost -U your_user -d whatsapp_server -f migrations/add_asset_generation_tables.sql
   ```

5. **Start the server**
   ```bash
   python main.py
   ```

### AWS Elastic Beanstalk Deployment (Production)

1. **Prepare Application**

   ```bash
   git clone <repository-url>
   cd whatsapp-assids-generate-server
   cp .env.example .env
   # Edit .env with your AWS RDS and S3 configuration
   ```

2. **Initialize and Deploy**

   ```bash
   # Install EB CLI
   pip install awsebcli

   # Initialize EB application
   eb init whatsapp-asset-server --platform python-3.11 --region us-east-1

   # Create environment
   eb create production --instance-type t3.medium --min-instances 1 --max-instances 5

   # Set environment variables
   eb setenv DATABASE_URL="postgresql://user:pass@your-rds-endpoint:5432/whatsapp_server"
   eb setenv AWS_ACCESS_KEY_ID="your-access-key"
   eb setenv AWS_SECRET_ACCESS_KEY="your-secret-key"
   eb setenv S3_BUCKET_NAME="your-bucket-name"

   # Deploy
   eb deploy
   ```

3. **Apply Database Migration**
   ```bash
   psql -h your-rds-endpoint -U your-user -d whatsapp_server -f migrations/add_asset_generation_tables.sql
   ```

## Configuration

### Environment Variables

| Variable                     | Description                      | Default         |
| ---------------------------- | -------------------------------- | --------------- |
| `DATABASE_URL`               | PostgreSQL connection string     | Required        |
| `AWS_ACCESS_KEY_ID`          | AWS access key                   | Required        |
| `AWS_SECRET_ACCESS_KEY`      | AWS secret key                   | Required        |
| `AWS_REGION`                 | AWS region                       | `us-east-1`     |
| `S3_BUCKET_NAME`             | S3 bucket name                   | Required        |
| `DEBUG`                      | Enable debug mode                | `False`         |
| `LOG_LEVEL`                  | Logging level                    | `INFO`          |
| `CRON_ENABLED`               | Enable cron scheduler            | `True`          |
| `ASSET_TEMP_DIR`             | Temporary directory for assets   | `./temp_assets` |
| `MAX_CONCURRENT_GENERATIONS` | Max concurrent asset generations | `5`             |

### AWS Elastic Beanstalk Configuration

The application includes pre-configured EB settings:

- **Platform**: Python 3.11
- **Instance Type**: t3.medium (recommended minimum)
- **Auto Scaling**: 1-5 instances
- **Health Checks**: Enhanced monitoring enabled
- **Log Collection**: Application logs automatically collected

#### Required EB Environment Variables

Set these using `eb setenv`:

```bash
eb setenv DATABASE_URL="postgresql://user:pass@your-rds-endpoint:5432/whatsapp_server"
eb setenv AWS_ACCESS_KEY_ID="your-access-key"
eb setenv AWS_SECRET_ACCESS_KEY="your-secret-key"
eb setenv S3_BUCKET_NAME="your-bucket-name"
eb setenv DEBUG="False"
eb setenv LOG_LEVEL="INFO"
eb setenv CRON_ENABLED="True"
eb setenv MAX_CONCURRENT_GENERATIONS="10"
```

## Database Schema

### New Tables

#### `asset_generate_files`

Stores Python code files for generating assets:

- `id`: UUID primary key
- `template_id`: Reference to templates table
- `file_name`: Name of the asset generation file
- `file_content`: Python code content
- `description`: Description of the asset generator
- `version`: Version of the code
- `is_active`: Whether the file is active

#### Updated Tables

**`campaigns`** - Added columns:

- `asset_generation_started_at`: When asset generation started
- `asset_generation_completed_at`: When asset generation completed
- `asset_generation_status`: Status of asset generation process

**`campaign_audience`** - Added columns:

- `asset_generation_status`: Individual member's asset generation status
- `generated_asset_urls`: JSON object with S3 URLs of generated assets

### Status Flow

```
Campaign Status Flow:
approved → asset_generation → asset_generated → ready_to_launch

Audience Member Status Flow:
pending → asset_generating → asset_generated → ready_to_send
```

## Asset Generation

### Creating Asset Generation Files

Asset generation files are Python modules stored in the database that implement a `generate_asset` function:

```python
def generate_asset(attributes, name, msisdn, temp_dir):
    """
    Generate personalized assets for an audience member

    Args:
        attributes: Dict with custom attributes from campaign_audience
        name: Audience member name
        msisdn: Phone number
        temp_dir: Temporary directory to save files

    Returns:
        Dict with asset types and file paths
        Example: {"image": "/path/to/image.png", "video": "/path/to/video.mp4"}
    """
    # Your asset generation logic here
    return {"image": image_path, "video": video_path}
```

### Example Asset Generators

See `examples/sample_asset_generator.py` for a complete example that generates:

- Personalized images with PIL
- Custom text content
- JSON data files
- QR codes (optional)

## API Endpoints

### Campaign Status

- `GET /api/v1/campaigns/{campaign_id}/status` - Get campaign status
- `PUT /api/v1/campaigns/{campaign_id}/status` - Update campaign status
- `GET /api/v1/campaigns/status/{status}` - Get campaigns by status

### Audience Management

- `GET /api/v1/campaigns/{campaign_id}/audience` - Get audience members
- Filter by `message_status` and `asset_generation_status` query parameters

### System Monitoring

- `GET /health` - Basic health check
- `GET /api/v1/health/detailed` - Comprehensive system health check
- `GET /api/v1/stats/overview` - System statistics
- `GET /api/v1/monitoring/stuck-processes` - Get stuck processes report

### Recovery Management

- `POST /api/v1/recovery/startup` - Manually trigger startup recovery
- `POST /api/v1/recovery/runtime` - Manually trigger runtime recovery
- `GET /api/v1/recovery/statistics` - Get recovery statistics

## Fault Tolerance & Recovery

The asset generation server is designed to handle various failure scenarios and automatically recover from issues:

### Automatic Recovery Features

1. **Startup Recovery**: On server restart, automatically detects and recovers:

   - Campaigns stuck in `asset_generation` status
   - Audience members stuck in `asset_generating` status
   - Incomplete campaigns that need to be resumed
   - Orphaned processing states

2. **Runtime Recovery**: Periodic checks (every 5 minutes) for:

   - Processes stuck for more than 30 minutes
   - Failed generations that can be retried
   - System resource issues

3. **Retry Mechanism**:

   - Automatic retry up to 3 times for failed asset generations
   - Exponential backoff for retries
   - Detailed error tracking and reporting

4. **Progress Tracking**:
   - Real-time progress updates for campaigns
   - Batch processing with progress checkpoints
   - Resume from last successful checkpoint

### Recovery Scenarios Handled

- **Server Crash**: Automatically resumes incomplete campaigns on restart
- **Database Connection Loss**: Reconnects and resumes operations
- **S3 Upload Failures**: Retries with exponential backoff
- **Asset Generation Timeouts**: Marks as failed and retries if under limit
- **Memory/CPU Issues**: Monitors system resources and adjusts processing

### Manual Recovery Options

Use the API endpoints to manually trigger recovery:

```bash
# Trigger startup recovery
curl -X POST http://localhost:8000/api/v1/recovery/startup

# Trigger runtime recovery check
curl -X POST http://localhost:8000/api/v1/recovery/runtime

# Get recovery statistics
curl http://localhost:8000/api/v1/recovery/statistics
```

## Monitoring and Logging

### Log Files

- `logs/asset_generator.log` - General application logs
- `logs/asset_generator.json` - Structured JSON logs
- `logs/errors.log` - Error-only logs

### Log Levels

- `DEBUG`: Detailed debugging information
- `INFO`: General information about asset generation
- `WARNING`: Warning messages
- `ERROR`: Error messages with stack traces
- `CRITICAL`: Critical errors

### Monitoring Metrics

- Campaign processing status
- Asset generation success/failure rates
- S3 upload statistics
- Database connection health

### AWS Elastic Beanstalk Monitoring

When deployed on EB, additional monitoring is available:

- **EB Health Dashboard**: Monitor application health and performance
- **CloudWatch Logs**: Centralized log collection and analysis
- **CloudWatch Metrics**: CPU, memory, and request metrics
- **Auto Scaling**: Automatic scaling based on load

#### EB Management Commands

```bash
# Check application status
eb status

# View application health
eb health

# View logs
eb logs

# SSH into instance (if needed)
eb ssh

# Monitor in real-time
eb health --refresh
```

## Troubleshooting

### Common Issues

1. **Asset generation fails**

   - Check the asset generation code in `asset_generate_files` table
   - Verify required Python packages are installed
   - Check temp directory permissions

2. **S3 upload fails**

   - Verify AWS credentials and permissions
   - Check S3 bucket exists and is accessible
   - Verify network connectivity to AWS

3. **Database connection issues**
   - Check database URL and credentials
   - Verify database server is running
   - Check network connectivity

### AWS Elastic Beanstalk Specific Issues

1. **Deployment fails**

   ```bash
   # Check deployment logs
   eb logs

   # Verify platform version
   eb platform show

   # Check configuration
   eb config
   ```

2. **Environment variables not set**

   ```bash
   # List current environment variables
   eb printenv

   # Set missing variables
   eb setenv KEY=VALUE
   ```

3. **Application not starting**

   ```bash
   # Check application logs
   eb logs --all

   # SSH into instance for debugging
   eb ssh

   # Check process status
   sudo supervisorctl status
   ```

4. **Auto-scaling issues**

   ```bash
   # Check auto-scaling configuration
   eb config

   # Monitor scaling events
   eb health --refresh
   ```

### Debug Mode

Enable debug mode by setting `DEBUG=True` in environment variables for:

- Detailed SQL query logging
- Extended error messages
- Additional debug information

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest
```

### Code Structure

- `main.py` - FastAPI application entry point
- `cron_scheduler.py` - Cron job implementation
- `asset_generator.py` - Core asset generation engine
- `s3_uploader.py` - S3 integration
- `campaign_manager.py` - Campaign status management
- `database.py` - Database models and connection
- `logger_config.py` - Logging configuration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Your License Here]
#   w h a t s a p p - a s s i d s - g e n e r a t e - s e r v e r 
 
 
