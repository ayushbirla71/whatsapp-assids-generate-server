from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database
    database_url: str
    
    # AWS S3
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "us-east-1"
    s3_bucket_name: str
    
    # Application
    debug: bool = False
    log_level: str = "INFO"
    cron_enabled: bool = True
    
    # Asset Generation
    asset_temp_dir: str = "./temp_assets"
    max_concurrent_generations: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()

# Ensure temp directory exists
os.makedirs(settings.asset_temp_dir, exist_ok=True)
