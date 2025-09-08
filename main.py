import asyncio
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

from config import settings
from database import init_db
from cron_scheduler import start_cron_scheduler, stop_cron_scheduler
from api_routes import router
from logger_config import setup_logging, get_logger

# Setup comprehensive logging
setup_logging()
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting WhatsApp Asset Generation Server...")
    
    # Initialize database
    await init_db()
    
    # Start cron scheduler if enabled
    if settings.cron_enabled:
        await start_cron_scheduler()
        logger.info("Cron scheduler started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down WhatsApp Asset Generation Server...")
    if settings.cron_enabled:
        await stop_cron_scheduler()
        logger.info("Cron scheduler stopped")

app = FastAPI(
    title="WhatsApp Asset Generation Server",
    description="Server for generating assets for WhatsApp campaigns",
    version="1.0.0",
    lifespan=lifespan
)

# Include API routes
app.include_router(router)

@app.get("/")
async def root():
    return {"message": "WhatsApp Asset Generation Server is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "asset-generation-server"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
