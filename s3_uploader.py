import boto3
import logging
import os
from typing import Optional
from botocore.exceptions import ClientError, NoCredentialsError
import aiofiles
import asyncio
from concurrent.futures import ThreadPoolExecutor

from config import settings

logger = logging.getLogger(__name__)

class S3Uploader:
    def __init__(self):
        self.s3_client = None
        self.executor = ThreadPoolExecutor(max_workers=5)
        self._initialize_s3_client()

    def _initialize_s3_client(self):
        """Initialize S3 client with credentials"""
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region
            )
            logger.info("S3 client initialized successfully")
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise
        except Exception as e:
            logger.error(f"Error initializing S3 client: {e}")
            raise

    async def upload_file(self, file_path: str, s3_key: str) -> Optional[str]:
        """
        Upload a file to S3 bucket
        
        Args:
            file_path: Local path to the file to upload
            s3_key: S3 object key (path in bucket)
            
        Returns:
            S3 URL of uploaded file or None if failed
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None

            # Get file size for logging
            file_size = os.path.getsize(file_path)
            logger.info(f"Uploading file {file_path} ({file_size} bytes) to S3 key: {s3_key}")

            # Determine content type based on file extension
            content_type = self._get_content_type(file_path)

            # Upload file in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self._upload_file_sync,
                file_path,
                s3_key,
                content_type
            )

            # Generate the S3 URL
            s3_url = f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"
            logger.info(f"File uploaded successfully to: {s3_url}")
            
            return s3_url

        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"AWS S3 error ({error_code}): {e}")
            return None
        except Exception as e:
            logger.error(f"Error uploading file to S3: {e}", exc_info=True)
            return None

    def _upload_file_sync(self, file_path: str, s3_key: str, content_type: str):
        """Synchronous file upload to S3"""
        extra_args = {
            'ContentType': content_type,
            'ServerSideEncryption': 'AES256'
        }
        
        # Add cache control for media files
        if content_type.startswith(('image/', 'video/', 'audio/')):
            extra_args['CacheControl'] = 'max-age=31536000'  # 1 year

        self.s3_client.upload_file(
            file_path,
            settings.s3_bucket_name,
            s3_key,
            ExtraArgs=extra_args
        )

    def _get_content_type(self, file_path: str) -> str:
        """Determine content type based on file extension"""
        extension = os.path.splitext(file_path)[1].lower()
        
        content_types = {
            # Images
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
            '.svg': 'image/svg+xml',
            
            # Videos
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.wmv': 'video/x-ms-wmv',
            '.flv': 'video/x-flv',
            '.webm': 'video/webm',
            '.mkv': 'video/x-matroska',
            
            # Audio
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.ogg': 'audio/ogg',
            '.aac': 'audio/aac',
            '.flac': 'audio/flac',
            
            # Documents
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain',
            '.json': 'application/json',
            '.xml': 'application/xml',
            
            # Archives
            '.zip': 'application/zip',
            '.rar': 'application/x-rar-compressed',
            '.7z': 'application/x-7z-compressed',
        }
        
        return content_types.get(extension, 'application/octet-stream')

    async def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3 bucket
        
        Args:
            s3_key: S3 object key to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self.s3_client.delete_object,
                {'Bucket': settings.s3_bucket_name, 'Key': s3_key}
            )
            
            logger.info(f"File deleted from S3: {s3_key}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"AWS S3 error deleting file ({error_code}): {e}")
            return False
        except Exception as e:
            logger.error(f"Error deleting file from S3: {e}", exc_info=True)
            return False

    async def file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in S3 bucket
        
        Args:
            s3_key: S3 object key to check
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self.s3_client.head_object,
                {'Bucket': settings.s3_bucket_name, 'Key': s3_key}
            )
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                return False
            logger.error(f"AWS S3 error checking file existence ({error_code}): {e}")
            return False
        except Exception as e:
            logger.error(f"Error checking file existence in S3: {e}", exc_info=True)
            return False

    def get_presigned_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for S3 object
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL or None if failed
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': settings.s3_bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"AWS S3 error generating presigned URL ({error_code}): {e}")
            return None
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}", exc_info=True)
            return None
