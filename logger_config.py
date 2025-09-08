import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional
import json
import traceback

from config import settings

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields if present
        if hasattr(record, 'campaign_id'):
            log_entry['campaign_id'] = record.campaign_id
        if hasattr(record, 'audience_id'):
            log_entry['audience_id'] = record.audience_id
        if hasattr(record, 'template_id'):
            log_entry['template_id'] = record.template_id
        if hasattr(record, 'organization_id'):
            log_entry['organization_id'] = record.organization_id
        
        return json.dumps(log_entry)

def setup_logging():
    """Setup comprehensive logging configuration"""
    
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colored output
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    
    # File handler for general logs
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'asset_generator.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    
    # JSON file handler for structured logs
    json_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'asset_generator.json'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    json_handler.setFormatter(JSONFormatter())
    json_handler.setLevel(logging.INFO)
    root_logger.addHandler(json_handler)
    
    # Error file handler for errors only
    error_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'errors.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    error_handler.setFormatter(file_formatter)
    error_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_handler)
    
    # Set specific logger levels
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

class AssetGenerationLogger:
    """Specialized logger for asset generation with context"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.context = {}
    
    def set_context(self, **kwargs):
        """Set context for all subsequent log messages"""
        self.context.update(kwargs)
    
    def clear_context(self):
        """Clear all context"""
        self.context.clear()
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log message with context"""
        extra = {**self.context, **kwargs}
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, exc_info: bool = False, **kwargs):
        self._log_with_context(logging.ERROR, message, **kwargs)
        if exc_info:
            self.logger.error(message, exc_info=True, extra={**self.context, **kwargs})
    
    def critical(self, message: str, exc_info: bool = False, **kwargs):
        self._log_with_context(logging.CRITICAL, message, **kwargs)
        if exc_info:
            self.logger.critical(message, exc_info=True, extra={**self.context, **kwargs})

def get_logger(name: str) -> AssetGenerationLogger:
    """Get a logger with asset generation context support"""
    return AssetGenerationLogger(name)

class ErrorHandler:
    """Centralized error handling for asset generation"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    async def handle_campaign_error(
        self, 
        campaign_id: str, 
        error: Exception, 
        context: Optional[dict] = None
    ):
        """Handle campaign-level errors"""
        self.logger.set_context(campaign_id=campaign_id)
        
        error_context = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {}
        }
        
        self.logger.error(
            f"Campaign error: {error}",
            exc_info=True,
            **error_context
        )
        
        # Here you could add additional error handling like:
        # - Sending alerts
        # - Updating database status
        # - Triggering retry mechanisms
    
    async def handle_audience_error(
        self, 
        campaign_id: str, 
        audience_id: str, 
        error: Exception, 
        context: Optional[dict] = None
    ):
        """Handle audience member-level errors"""
        self.logger.set_context(campaign_id=campaign_id, audience_id=audience_id)
        
        error_context = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {}
        }
        
        self.logger.error(
            f"Audience member error: {error}",
            exc_info=True,
            **error_context
        )
    
    async def handle_s3_error(
        self, 
        operation: str, 
        file_path: str, 
        s3_key: str, 
        error: Exception
    ):
        """Handle S3-related errors"""
        error_context = {
            'operation': operation,
            'file_path': file_path,
            's3_key': s3_key,
            'error_type': type(error).__name__,
            'error_message': str(error)
        }
        
        self.logger.error(
            f"S3 {operation} error: {error}",
            exc_info=True,
            **error_context
        )
    
    async def handle_database_error(
        self, 
        operation: str, 
        error: Exception, 
        context: Optional[dict] = None
    ):
        """Handle database-related errors"""
        error_context = {
            'operation': operation,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {}
        }
        
        self.logger.error(
            f"Database {operation} error: {error}",
            exc_info=True,
            **error_context
        )

# Global error handler instance
error_handler = ErrorHandler()

# Performance monitoring decorator
def monitor_performance(func):
    """Decorator to monitor function performance"""
    import time
    import functools
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        logger = get_logger(func.__module__)
        
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            logger.info(
                f"Function {func.__name__} completed successfully",
                execution_time=execution_time,
                function_name=func.__name__
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            logger.error(
                f"Function {func.__name__} failed",
                exc_info=True,
                execution_time=execution_time,
                function_name=func.__name__,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            
            raise
    
    return wrapper
