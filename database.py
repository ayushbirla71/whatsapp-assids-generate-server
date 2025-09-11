from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID, ENUM
import uuid
from datetime import datetime
import enum
from config import settings

# Create async engine
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.debug
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

Base = declarative_base()

# Define PostgreSQL ENUM types to match existing schema
campaign_status_enum = ENUM(
    'draft', 'pending_approval', 'approved', 'rejected', 'scheduled',
    'asset_generation', 'asset_generated', 'ready_to_launch', 'running',
    'paused', 'completed', 'cancelled',
    name='campaign_status'
)

asset_generation_status_enum = ENUM(
    'pending', 'processing', 'generated', 'failed',
    name='asset_generation_status'
)

message_status_extended_enum = ENUM(
    'pending', 'asset_generating', 'asset_generated', 'ready_to_send',
    'sent', 'delivered', 'read', 'failed',
    name='message_status_extended'
)

# Status constants for easy reference
class CampaignStatus:
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    ASSET_GENERATION = "asset_generation"
    ASSET_GENERATED = "asset_generated"
    READY_TO_LAUNCH = "ready_to_launch"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class AssetGenerationStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    GENERATED = "generated"
    FAILED = "failed"

class MessageStatus:
    PENDING = "pending"
    ASSET_GENERATING = "asset_generating"
    ASSET_GENERATED = "asset_generated"
    READY_TO_SEND = "ready_to_send"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"

# Asset Generation Files Model
class AssetGenerateFiles(Base):
    __tablename__ = "asset_generate_files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("templates.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_content = Column(Text, nullable=False)  # The actual Python code
    description = Column(Text)
    version = Column(String(50), default="1.0")
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True))

# Organizations Model (reference)
class Organizations(Base):
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    # ... other fields as per your schema

# Templates Model (reference)
class Templates(Base):
    __tablename__ = "templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    # ... other fields as per your schema

# Updated Campaigns Model
class Campaigns(Base):
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("templates.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(campaign_status_enum, default=CampaignStatus.DRAFT)

    # Asset generation tracking
    asset_generation_started_at = Column(DateTime)
    asset_generation_completed_at = Column(DateTime)
    asset_generation_status = Column(asset_generation_status_enum)
    asset_generation_retry_count = Column(Integer, default=0)
    asset_generation_last_error = Column(Text)
    asset_generation_progress = Column(JSON, default={})  # Track progress details

    # ... other fields as per your schema
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Updated Campaign Audience Model
class CampaignAudience(Base):
    __tablename__ = "campaign_audience"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    msisdn = Column(Text, nullable=False)
    attributes = Column(JSON, default={})

    # Message and asset status
    message_status = Column(message_status_extended_enum, default=MessageStatus.PENDING)
    asset_generation_status = Column(asset_generation_status_enum)

    # Asset URLs (after generation and S3 upload)
    generated_asset_urls = Column(JSON, default={})  # {"image": "s3://...", "video": "s3://..."}

    # Error handling and retry tracking
    asset_generation_retry_count = Column(Integer, default=0)
    asset_generation_last_error = Column(Text)
    asset_generation_started_at = Column(DateTime)
    asset_generation_completed_at = Column(DateTime)

    # ... other fields as per your schema
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        # Only create new tables, don't drop existing ones
        await conn.run_sync(Base.metadata.create_all)
