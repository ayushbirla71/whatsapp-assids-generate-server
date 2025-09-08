import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import (
    AsyncSessionLocal, Campaigns, CampaignAudience,
    CampaignStatus, AssetGenerationStatus, MessageStatus
)
from logger_config import get_logger, monitor_performance
from config import settings

logger = get_logger(__name__)

class RecoveryManager:
    """Handles recovery of stuck or failed asset generation processes"""
    
    def __init__(self):
        self.max_retry_count = 3
        self.stuck_timeout_minutes = 30  # Consider process stuck after 30 minutes
        self.recovery_batch_size = 10
    
    @monitor_performance
    async def perform_startup_recovery(self):
        """Perform recovery operations on server startup"""
        logger.info("Starting recovery operations...")
        
        try:
            # 1. Recover stuck campaigns
            stuck_campaigns = await self._find_stuck_campaigns()
            if stuck_campaigns:
                logger.info(f"Found {len(stuck_campaigns)} stuck campaigns")
                await self._recover_stuck_campaigns(stuck_campaigns)
            
            # 2. Recover stuck audience members
            stuck_audience = await self._find_stuck_audience_members()
            if stuck_audience:
                logger.info(f"Found {len(stuck_audience)} stuck audience members")
                await self._recover_stuck_audience_members(stuck_audience)
            
            # 3. Resume incomplete campaigns
            incomplete_campaigns = await self._find_incomplete_campaigns()
            if incomplete_campaigns:
                logger.info(f"Found {len(incomplete_campaigns)} incomplete campaigns to resume")
                await self._resume_incomplete_campaigns(incomplete_campaigns)
            
            # 4. Clean up orphaned processing states
            await self._cleanup_orphaned_states()
            
            logger.info("Recovery operations completed successfully")
            
        except Exception as e:
            logger.error(f"Error during startup recovery: {e}", exc_info=True)
            raise

    async def _find_stuck_campaigns(self) -> List[Campaigns]:
        """Find campaigns that are stuck in processing state"""
        async with AsyncSessionLocal() as session:
            try:
                cutoff_time = datetime.utcnow() - timedelta(minutes=self.stuck_timeout_minutes)
                
                query = select(Campaigns).where(
                    and_(
                        Campaigns.status == CampaignStatus.ASSET_GENERATION,
                        Campaigns.asset_generation_status == AssetGenerationStatus.PROCESSING,
                        Campaigns.asset_generation_started_at < cutoff_time
                    )
                )
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except Exception as e:
                logger.error(f"Error finding stuck campaigns: {e}", exc_info=True)
                return []

    async def _find_stuck_audience_members(self) -> List[CampaignAudience]:
        """Find audience members stuck in processing state"""
        async with AsyncSessionLocal() as session:
            try:
                cutoff_time = datetime.utcnow() - timedelta(minutes=self.stuck_timeout_minutes)
                
                query = select(CampaignAudience).where(
                    and_(
                        CampaignAudience.message_status == MessageStatus.ASSET_GENERATING,
                        CampaignAudience.asset_generation_status == AssetGenerationStatus.PROCESSING,
                        CampaignAudience.asset_generation_started_at < cutoff_time
                    )
                )
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except Exception as e:
                logger.error(f"Error finding stuck audience members: {e}", exc_info=True)
                return []

    async def _find_incomplete_campaigns(self) -> List[Campaigns]:
        """Find campaigns that were interrupted during asset generation"""
        async with AsyncSessionLocal() as session:
            try:
                # Find campaigns in asset_generation status but not all audience members are processed
                query = select(Campaigns).where(
                    and_(
                        Campaigns.status == CampaignStatus.ASSET_GENERATION,
                        or_(
                            Campaigns.asset_generation_status.is_(None),
                            Campaigns.asset_generation_status == AssetGenerationStatus.PENDING
                        )
                    )
                )
                
                result = await session.execute(query)
                campaigns = result.scalars().all()
                
                # Filter campaigns that actually have pending audience members
                incomplete_campaigns = []
                for campaign in campaigns:
                    has_pending = await self._has_pending_audience_members(session, campaign.id)
                    if has_pending:
                        incomplete_campaigns.append(campaign)
                
                return incomplete_campaigns
                
            except Exception as e:
                logger.error(f"Error finding incomplete campaigns: {e}", exc_info=True)
                return []

    async def _has_pending_audience_members(self, session: AsyncSession, campaign_id) -> bool:
        """Check if campaign has audience members that need asset generation"""
        try:
            query = select(CampaignAudience).where(
                and_(
                    CampaignAudience.campaign_id == campaign_id,
                    or_(
                        CampaignAudience.asset_generation_status.is_(None),
                        CampaignAudience.asset_generation_status == AssetGenerationStatus.PENDING,
                        and_(
                            CampaignAudience.asset_generation_status == AssetGenerationStatus.FAILED,
                            CampaignAudience.asset_generation_retry_count < self.max_retry_count
                        )
                    )
                )
            ).limit(1)
            
            result = await session.execute(query)
            return result.scalar_one_or_none() is not None
            
        except Exception as e:
            logger.error(f"Error checking pending audience members: {e}", exc_info=True)
            return False

    async def _recover_stuck_campaigns(self, campaigns: List[Campaigns]):
        """Recover stuck campaigns by resetting their status"""
        async with AsyncSessionLocal() as session:
            try:
                for campaign in campaigns:
                    logger.info(f"Recovering stuck campaign: {campaign.name} (ID: {campaign.id})")
                    
                    # Reset campaign status
                    campaign.asset_generation_status = AssetGenerationStatus.PENDING
                    campaign.asset_generation_retry_count += 1
                    campaign.asset_generation_last_error = "Recovered from stuck state after server restart"
                    
                    # Update progress tracking
                    progress = campaign.asset_generation_progress or {}
                    progress['recovery_count'] = progress.get('recovery_count', 0) + 1
                    progress['last_recovery_at'] = datetime.utcnow().isoformat()
                    campaign.asset_generation_progress = progress
                    
                    session.add(campaign)
                
                await session.commit()
                logger.info(f"Recovered {len(campaigns)} stuck campaigns")
                
            except Exception as e:
                logger.error(f"Error recovering stuck campaigns: {e}", exc_info=True)
                await session.rollback()

    async def _recover_stuck_audience_members(self, audience_members: List[CampaignAudience]):
        """Recover stuck audience members by resetting their status"""
        async with AsyncSessionLocal() as session:
            try:
                for member in audience_members:
                    logger.info(f"Recovering stuck audience member: {member.name} (ID: {member.id})")
                    
                    # Reset status for retry
                    if member.asset_generation_retry_count < self.max_retry_count:
                        member.message_status = MessageStatus.PENDING
                        member.asset_generation_status = AssetGenerationStatus.PENDING
                        member.asset_generation_retry_count += 1
                        member.asset_generation_last_error = "Recovered from stuck state after server restart"
                    else:
                        # Max retries reached, mark as failed
                        member.message_status = MessageStatus.FAILED
                        member.asset_generation_status = AssetGenerationStatus.FAILED
                        member.asset_generation_last_error = "Max retries exceeded after recovery"
                        member.asset_generation_completed_at = datetime.utcnow()
                    
                    session.add(member)
                
                await session.commit()
                logger.info(f"Recovered {len(audience_members)} stuck audience members")
                
            except Exception as e:
                logger.error(f"Error recovering stuck audience members: {e}", exc_info=True)
                await session.rollback()

    async def _resume_incomplete_campaigns(self, campaigns: List[Campaigns]):
        """Resume incomplete campaigns by updating their status"""
        async with AsyncSessionLocal() as session:
            try:
                for campaign in campaigns:
                    logger.info(f"Resuming incomplete campaign: {campaign.name} (ID: {campaign.id})")
                    
                    # Update campaign to be picked up by cron job
                    campaign.status = CampaignStatus.APPROVED  # Reset to approved so cron picks it up
                    campaign.asset_generation_status = None  # Reset generation status
                    
                    # Update progress tracking
                    progress = campaign.asset_generation_progress or {}
                    progress['resume_count'] = progress.get('resume_count', 0) + 1
                    progress['last_resume_at'] = datetime.utcnow().isoformat()
                    campaign.asset_generation_progress = progress
                    
                    session.add(campaign)
                
                await session.commit()
                logger.info(f"Resumed {len(campaigns)} incomplete campaigns")
                
            except Exception as e:
                logger.error(f"Error resuming incomplete campaigns: {e}", exc_info=True)
                await session.rollback()

    async def _cleanup_orphaned_states(self):
        """Clean up any orphaned processing states"""
        async with AsyncSessionLocal() as session:
            try:
                # Reset any audience members that are in asset_generating state but campaign is not in asset_generation
                query = select(CampaignAudience).join(Campaigns).where(
                    and_(
                        CampaignAudience.message_status == MessageStatus.ASSET_GENERATING,
                        Campaigns.status != CampaignStatus.ASSET_GENERATION
                    )
                )
                
                result = await session.execute(query)
                orphaned_members = result.scalars().all()
                
                if orphaned_members:
                    logger.info(f"Cleaning up {len(orphaned_members)} orphaned audience member states")
                    
                    for member in orphaned_members:
                        member.message_status = MessageStatus.PENDING
                        member.asset_generation_status = AssetGenerationStatus.PENDING
                        session.add(member)
                    
                    await session.commit()
                
            except Exception as e:
                logger.error(f"Error cleaning up orphaned states: {e}", exc_info=True)
                await session.rollback()

    async def check_and_recover_during_runtime(self):
        """Periodic check for stuck processes during runtime"""
        try:
            # Find and recover stuck processes
            stuck_campaigns = await self._find_stuck_campaigns()
            if stuck_campaigns:
                logger.warning(f"Found {len(stuck_campaigns)} stuck campaigns during runtime")
                await self._recover_stuck_campaigns(stuck_campaigns)
            
            stuck_audience = await self._find_stuck_audience_members()
            if stuck_audience:
                logger.warning(f"Found {len(stuck_audience)} stuck audience members during runtime")
                await self._recover_stuck_audience_members(stuck_audience)
                
        except Exception as e:
            logger.error(f"Error during runtime recovery check: {e}", exc_info=True)

    async def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get statistics about recovery operations"""
        async with AsyncSessionLocal() as session:
            try:
                # Count campaigns by recovery status
                campaigns_with_retries = await session.execute(
                    select(Campaigns).where(Campaigns.asset_generation_retry_count > 0)
                )
                
                audience_with_retries = await session.execute(
                    select(CampaignAudience).where(CampaignAudience.asset_generation_retry_count > 0)
                )
                
                return {
                    "campaigns_recovered": len(campaigns_with_retries.scalars().all()),
                    "audience_members_recovered": len(audience_with_retries.scalars().all()),
                    "max_retry_count": self.max_retry_count,
                    "stuck_timeout_minutes": self.stuck_timeout_minutes
                }
                
            except Exception as e:
                logger.error(f"Error getting recovery statistics: {e}", exc_info=True)
                return {}
