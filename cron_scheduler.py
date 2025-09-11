import asyncio
import logging
from datetime import datetime
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal, Campaigns, CampaignStatus, AssetGenerationStatus
from asset_generator import AssetGenerationManager
from recovery_manager import RecoveryManager
from logger_config import get_logger, monitor_performance

logger = get_logger(__name__)

class CronScheduler:
    def __init__(self):
        self.running = False
        self.task = None
        self.recovery_task = None
        self.asset_manager = AssetGenerationManager()
        self.recovery_manager = RecoveryManager()
        self.recovery_check_interval = 300  # 5 minutes

    async def start(self):
        """Start the cron scheduler"""
        if self.running:
            logger.warning("Cron scheduler is already running")
            return

        # Perform startup recovery first
        logger.info("Performing startup recovery...")
        try:
            await self.recovery_manager.perform_startup_recovery()
        except Exception as e:
            logger.error(f"Startup recovery failed: {e}", exc_info=True)

        self.running = True
        self.task = asyncio.create_task(self._run_scheduler())
        self.recovery_task = asyncio.create_task(self._run_recovery_checker())
        logger.info("Cron scheduler and recovery checker started")

    async def stop(self):
        """Stop the cron scheduler"""
        if not self.running:
            return

        self.running = False

        # Stop main scheduler task
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        # Stop recovery checker task
        if self.recovery_task:
            self.recovery_task.cancel()
            try:
                await self.recovery_task
            except asyncio.CancelledError:
                pass

        logger.info("Cron scheduler and recovery checker stopped")

    async def _run_scheduler(self):
        """Main scheduler loop - runs every minute"""
        while self.running:
            try:
                await self._check_and_process_campaigns()
                # Wait for 60 seconds (1 minute)
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cron scheduler: {e}", exc_info=True)
                # Wait a bit before retrying to avoid rapid error loops
                await asyncio.sleep(10)

    async def _check_and_process_campaigns(self):
        """Check for approved campaigns and trigger asset generation"""
        async with AsyncSessionLocal() as session:
            try:
                # Find campaigns that are approved and ready for asset generation
                # Use string comparison to avoid enum type conflicts
                query = select(Campaigns).where(
                    Campaigns.status == 'approved'
                )

                result = await session.execute(query)
                campaigns = result.scalars().all()

                if campaigns:
                    logger.info(f"Found {len(campaigns)} campaigns ready for asset generation")

                for campaign in campaigns:
                    try:
                        await self._process_campaign(session, campaign)
                    except Exception as e:
                        logger.error(f"Error processing campaign {campaign.id}: {e}", exc_info=True)
                        # Mark campaign as failed with error details
                        campaign.asset_generation_status = AssetGenerationStatus.FAILED
                        campaign.asset_generation_last_error = str(e)
                        campaign.asset_generation_retry_count += 1
                        await session.commit()

            except Exception as e:
                logger.error(f"Error checking campaigns: {e}", exc_info=True)

    async def _process_campaign(self, session: AsyncSession, campaign: Campaigns):
        """Process a single campaign for asset generation"""
        logger.info(f"Starting asset generation for campaign: {campaign.name} (ID: {campaign.id})")
        
        # Update campaign status to indicate asset generation has started
        campaign.status = CampaignStatus.ASSET_GENERATION
        # Skip setting asset_generation_status for now to avoid schema conflicts
        # campaign.asset_generation_status = AssetGenerationStatus.PROCESSING
        # campaign.asset_generation_started_at = datetime.utcnow()
        await session.commit()
        
        # Trigger asset generation in background with error handling
        asyncio.create_task(
            self._safe_generate_campaign_assets(campaign.id)
        )

    async def _safe_generate_campaign_assets(self, campaign_id):
        """Safely generate campaign assets with error handling"""
        try:
            await self.asset_manager.generate_campaign_assets(campaign_id)
        except Exception as e:
            logger.error(f"Error in asset generation for campaign {campaign_id}: {e}", exc_info=True)
            # Update campaign status to failed
            async with AsyncSessionLocal() as session:
                campaign = await session.get(Campaigns, campaign_id)
                if campaign:
                    campaign.asset_generation_status = AssetGenerationStatus.FAILED
                    campaign.asset_generation_last_error = str(e)
                    campaign.asset_generation_retry_count += 1
                    await session.commit()

    async def _run_recovery_checker(self):
        """Recovery checker loop - runs every 5 minutes"""
        while self.running:
            try:
                await self.recovery_manager.check_and_recover_during_runtime()
                # Wait for recovery check interval
                await asyncio.sleep(self.recovery_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in recovery checker: {e}", exc_info=True)
                # Wait a bit before retrying to avoid rapid error loops
                await asyncio.sleep(60)

# Global scheduler instance
_scheduler = None

async def start_cron_scheduler():
    """Start the global cron scheduler"""
    global _scheduler
    if _scheduler is None:
        _scheduler = CronScheduler()
    await _scheduler.start()

async def stop_cron_scheduler():
    """Stop the global cron scheduler"""
    global _scheduler
    if _scheduler:
        await _scheduler.stop()
