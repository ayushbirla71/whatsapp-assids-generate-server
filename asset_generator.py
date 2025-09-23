
import asyncio
import logging
import os
import tempfile
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import importlib.util
import sys
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import (
    AsyncSessionLocal, Campaigns, CampaignAudience, Templates, AssetGenerateFiles,
    CampaignStatus, AssetGenerationStatus, MessageStatus
)
from s3_uploader import S3Uploader
from logger_config import get_logger, monitor_performance
from config import settings

logger = get_logger(__name__)

class AssetGenerationManager:
    def __init__(self):
        self.s3_uploader = S3Uploader()
        self.active_generations = set()  # Track active generation tasks
        self.max_retry_count = 3
        self.generation_timeout = 1800  # 30 minutes timeout per campaign

    @monitor_performance
    async def generate_campaign_assets(self, campaign_id: uuid.UUID):
        """Generate assets for all audience members in a campaign"""
        if campaign_id in self.active_generations:
            logger.warning(f"Asset generation already in progress for campaign {campaign_id}")
            return

        self.active_generations.add(campaign_id)
        logger.set_context(campaign_id=str(campaign_id))

        try:
            # Set timeout for the entire campaign generation
            await asyncio.wait_for(
                self._process_campaign_generation(campaign_id),
                timeout=self.generation_timeout
            )

        except asyncio.TimeoutError:
            logger.error(f"Campaign {campaign_id} generation timed out after {self.generation_timeout} seconds")
            async with AsyncSessionLocal() as session:
                campaign = await session.get(Campaigns, campaign_id)
                if campaign:
                    await self._mark_campaign_failed(session, campaign, "Generation timeout")
        except Exception as e:
            logger.error(f"Error in asset generation for campaign {campaign_id}: {e}", exc_info=True)
            async with AsyncSessionLocal() as session:
                campaign = await session.get(Campaigns, campaign_id)
                if campaign:
                    await self._mark_campaign_failed(session, campaign, str(e))
        finally:
            self.active_generations.discard(campaign_id)
            logger.clear_context()

    async def _process_campaign_generation(self, campaign_id: uuid.UUID):
        """Process campaign generation with detailed progress tracking"""
        async with AsyncSessionLocal() as session:
            # Get campaign details
            campaign = await self._get_campaign_with_template(session, campaign_id)
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found")
                return

            # Get asset generation file
            asset_file = await self._get_asset_generation_file(session, campaign.template_id)
            if not asset_file:
                logger.error(f"No asset generation file found for template {campaign.template_id}")
                await self._mark_campaign_failed(session, campaign, "No asset generation file found")
                return

            logger.info(f"Asset generation file found: {asset_file}")
            # Get audience members that need processing (including failed ones that can be retried)
            audience_members = await self._get_pending_campaign_audience(session, campaign_id)
            if not audience_members:
                logger.info(f"No pending audience members found for campaign {campaign_id}")
                await self._check_and_complete_campaign(session, campaign)
                return

            logger.info(f"Starting asset generation for {len(audience_members)} audience members")

            # Initialize progress tracking
            progress = campaign.asset_generation_progress or {}
            progress.update({
                'total_audience': len(audience_members),
                'processed': 0,
                'successful': 0,
                'failed': 0,
                'started_at': datetime.utcnow().isoformat()
            })
            campaign.asset_generation_progress = progress
            await session.commit()

            # Process audience members in batches
            batch_size = min(settings.max_concurrent_generations, len(audience_members))

            for i in range(0, len(audience_members), batch_size):
                batch = audience_members[i:i + batch_size]

                # Process batch with individual error handling
                results = await asyncio.gather(*[
                    self._safe_generate_asset_for_audience_member(
                        campaign, asset_file, member
                    )
                    for member in batch
                ], return_exceptions=True)

                # Update progress
                successful = sum(1 for r in results if r is True)
                failed = sum(1 for r in results if r is False)

                progress['processed'] += len(batch)
                progress['successful'] += successful
                progress['failed'] += failed
                progress['last_batch_at'] = datetime.utcnow().isoformat()

                campaign.asset_generation_progress = progress
                await session.commit()

                logger.info(f"Batch completed: {successful} successful, {failed} failed")

            # Check if campaign is complete
            await self._check_and_complete_campaign(session, campaign)
            logger.info(f"Asset generation completed for campaign {campaign_id}")

    async def _get_campaign_with_template(self, session: AsyncSession, campaign_id: uuid.UUID) -> Optional[Campaigns]:
        """Get campaign with its template information"""
        query = select(Campaigns).where(Campaigns.id == campaign_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def _get_asset_generation_file(self, session: AsyncSession, template_id: uuid.UUID) -> Optional[AssetGenerateFiles]:
        """Get the asset generation file for a template"""
        query = select(AssetGenerateFiles).where(
            and_(
                AssetGenerateFiles.template_id == template_id,
                AssetGenerateFiles.is_active == True
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def _get_pending_campaign_audience(self, session: AsyncSession, campaign_id: uuid.UUID) -> List[CampaignAudience]:
        """Get audience members that need asset generation (including retryable failed ones)"""
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
        )
        result = await session.execute(query)
        return result.scalars().all()

    async def _safe_generate_asset_for_audience_member(
        self,
        campaign: Campaigns,
        asset_file: AssetGenerateFiles,
        audience_member: CampaignAudience
    ) -> bool:
        """Safely generate asset for audience member with error handling"""
        try:
            return await self._generate_asset_for_audience_member(
                campaign, asset_file, audience_member
            )
        except Exception as e:
            logger.error(f"Error generating asset for audience member {audience_member.id}: {e}", exc_info=True)

            # Use a separate session for error handling to avoid transaction conflicts
            async with AsyncSessionLocal() as error_session:
                try:
                    # Get fresh instance of audience member in the error session
                    fresh_audience_member = await error_session.get(CampaignAudience, audience_member.id)
                    if fresh_audience_member:
                        # Update audience member with error
                        fresh_audience_member.asset_generation_status = AssetGenerationStatus.FAILED
                        fresh_audience_member.asset_generation_last_error = str(e)
                        fresh_audience_member.asset_generation_retry_count += 1
                        fresh_audience_member.asset_generation_completed_at = datetime.utcnow()
                        fresh_audience_member.message_status = MessageStatus.FAILED
                        await error_session.commit()
                except Exception as commit_error:
                    logger.error(f"Failed to update error status for audience member {audience_member.id}: {commit_error}")
                    await error_session.rollback()

            return False

    async def _generate_asset_for_audience_member(
        self,
        campaign: Campaigns,
        asset_file: AssetGenerateFiles,
        audience_member: CampaignAudience
    ) -> bool:
        """Generate asset for a single audience member"""
        logger.set_context(audience_id=str(audience_member.id))

        # Use a dedicated session for this audience member to avoid transaction conflicts
        async with AsyncSessionLocal() as session:
            try:
                logger.info(f"Generating asset for audience member {audience_member.name}")

                # Get fresh instance of audience member in this session
                audience_member = await session.get(CampaignAudience, audience_member.id)
                if not audience_member:
                    logger.error(f"Audience member not found: {audience_member.id}")
                    return False

                # Update audience member status
                audience_member.message_status = MessageStatus.ASSET_GENERATING
                audience_member.asset_generation_status = AssetGenerationStatus.PROCESSING
                audience_member.asset_generation_started_at = datetime.utcnow()
                await session.commit()

                # Execute the asset generation code
                generated_assets = await self._execute_asset_generation_code(
                    asset_file, audience_member.attributes, audience_member
                )

                if generated_assets:
                    # Upload assets to S3
                    uploaded_urls = await self._upload_assets_to_s3(generated_assets, campaign.id, audience_member.id, asset_file.typeofcontent )

                    if uploaded_urls:
                        # Update audience member with asset URLs
                        audience_member.generated_asset_urls = uploaded_urls
                        audience_member.message_status = MessageStatus.ASSET_GENERATED
                        audience_member.asset_generation_status = AssetGenerationStatus.GENERATED
                        audience_member.asset_generation_completed_at = datetime.utcnow()

                        logger.info(f"Asset generation completed for audience member {audience_member.name}")
                        await session.commit()
                        return True
                    else:
                        # S3 upload failed
                        audience_member.asset_generation_status = AssetGenerationStatus.FAILED
                        audience_member.asset_generation_last_error = "S3 upload failed"
                        audience_member.asset_generation_completed_at = datetime.utcnow()
                        logger.error(f"S3 upload failed for audience member {audience_member.id}")
                else:
                    # Asset generation failed
                    audience_member.asset_generation_status = AssetGenerationStatus.FAILED
                    audience_member.asset_generation_last_error = "Asset generation returned no results"
                    audience_member.asset_generation_completed_at = datetime.utcnow()
                    logger.error(f"Asset generation failed for audience member {audience_member.id}")

                await session.commit()
                return False

            except Exception as e:
                logger.error(f"Error generating asset for audience member {audience_member.id}: {e}", exc_info=True)
                try:
                    audience_member.asset_generation_status = AssetGenerationStatus.FAILED
                    audience_member.asset_generation_last_error = str(e)
                    audience_member.asset_generation_completed_at = datetime.utcnow()
                    await session.commit()
                except Exception as commit_error:
                    logger.error(f"Failed to commit error status: {commit_error}")
                    await session.rollback()
                return False
            finally:
                logger.clear_context()

    async def  _execute_asset_generation_code(
        self, 
        asset_file: AssetGenerateFiles, 
        attributes: Dict[str, Any],
        audience_member: CampaignAudience
    ) -> Optional[Dict[str, str]]:
        """Execute the asset generation code and return generated file paths"""
        try:
            # Create a temporary directory for this generation
            with tempfile.TemporaryDirectory(dir=settings.asset_temp_dir) as temp_dir:
                # Create a temporary Python file with the asset generation code
                temp_file_path = os.path.join(temp_dir, f"{asset_file.file_name}.py")
                
                with open(temp_file_path, 'w') as f:
                    f.write(asset_file.file_content)

                # Load the module dynamically
                spec = importlib.util.spec_from_file_location("asset_generator", temp_file_path)
                module = importlib.util.module_from_spec(spec)
                
                # Add the temp directory to sys.path temporarily
                sys.path.insert(0, temp_dir)
                
                try:
                    spec.loader.exec_module(module)
                    
                    # The asset generation module should have a generate_asset function
                    if hasattr(module, 'generate_asset'):
                        # Call the generate_asset function with audience data
                        result = await asyncio.get_event_loop().run_in_executor(
                            None,
                            module.generate_asset,
                            attributes,
                            audience_member.name,
                            audience_member.msisdn,
                            temp_dir
                        )
                        return result
                    else:
                        logger.error(f"Asset generation file {asset_file.file_name} missing generate_asset function")
                        return None
                        
                finally:
                    # Remove temp directory from sys.path
                    sys.path.remove(temp_dir)

        except Exception as e:
            logger.error(f"Error executing asset generation code: {e}", exc_info=True)
            return None

    async def _upload_assets_to_s3(
        self, 
        assets: Dict[str, str], 
        campaign_id: uuid.UUID, 
        audience_id: uuid.UUID,
        typeofcontent: str
    ) -> Dict[str, str]:
        """Upload generated assets to S3 and return URLs"""
        uploaded_urls = {}
        logger.info(f"Uploading assets to S3 for audience member {audience_id}")
        logger.info(f"Type of content: {typeofcontent}")
        
        for asset_type, file_path in assets.items():
            try:
                 if typeofcontent == "public":
                    uploaded_urls[asset_type] = file_path
                    logger.info(f"Uploaded {asset_type} asset to S3: {file_path}")
                    
                 elif os.path.exists(file_path):
                    # Generate S3 key
                    file_extension = os.path.splitext(file_path)[1]
                    s3_key = f"campaigns/{campaign_id}/audience/{audience_id}/{asset_type}{file_extension}"

                    # Upload to S3
                    s3_url = await self.s3_uploader.upload_file(file_path, s3_key)
                    uploaded_urls[asset_type] = s3_url

                    logger.info(f"Uploaded {asset_type} asset to S3: {s3_url}")
                 else:
                    logger.warning(f"Asset file not found: {file_path}")
                    
            except Exception as e:
                logger.error(f"Error uploading {asset_type} asset: {e}", exc_info=True)
        
        return uploaded_urls

    async def _check_and_complete_campaign(self, session: AsyncSession, campaign: Campaigns):
        """Check if campaign is complete and update status accordingly"""
        try:
            # Count total audience members
            total_query = select(func.count(CampaignAudience.id)).where(
                CampaignAudience.campaign_id == campaign.id
            )
            total_result = await session.execute(total_query)
            total_count = total_result.scalar() or 0

            # Count completed audience members (generated or failed with max retries)
            completed_query = select(func.count(CampaignAudience.id)).where(
                and_(
                    CampaignAudience.campaign_id == campaign.id,
                    or_(
                        CampaignAudience.asset_generation_status == AssetGenerationStatus.GENERATED,
                        and_(
                            CampaignAudience.asset_generation_status == AssetGenerationStatus.FAILED,
                            CampaignAudience.asset_generation_retry_count >= self.max_retry_count
                        )
                    )
                )
            )
            completed_result = await session.execute(completed_query)
            completed_count = completed_result.scalar() or 0

            # Count successful generations
            success_query = select(func.count(CampaignAudience.id)).where(
                and_(
                    CampaignAudience.campaign_id == campaign.id,
                    CampaignAudience.asset_generation_status == AssetGenerationStatus.GENERATED
                )
            )
            success_result = await session.execute(success_query)
            success_count = success_result.scalar() or 0

            if total_count > 0 and completed_count == total_count:
                # Campaign is complete
                if success_count > 0:
                    # At least some assets were generated successfully
                    campaign.status = CampaignStatus.ASSET_GENERATED
                    campaign.asset_generation_status = AssetGenerationStatus.GENERATED
                    logger.info(f"Campaign {campaign.id} completed: {success_count}/{total_count} successful")
                else:
                    # All failed
                    campaign.asset_generation_status = AssetGenerationStatus.FAILED
                    campaign.asset_generation_last_error = "All audience members failed asset generation"
                    logger.error(f"Campaign {campaign.id} failed: all audience members failed")

                campaign.asset_generation_completed_at = datetime.utcnow()

                # Update final progress
                progress = campaign.asset_generation_progress or {}
                progress.update({
                    'completed_at': datetime.utcnow().isoformat(),
                    'final_total': total_count,
                    'final_successful': success_count,
                    'final_failed': total_count - success_count
                })
                campaign.asset_generation_progress = progress

                await session.commit()

        except Exception as e:
            logger.error(f"Error checking campaign completion: {e}", exc_info=True)

    async def _mark_campaign_failed(self, session: AsyncSession, campaign: Campaigns, error_message: str = None):
        """Mark campaign as asset generation failed"""
        campaign.asset_generation_status = AssetGenerationStatus.FAILED
        campaign.asset_generation_completed_at = datetime.utcnow()
        if error_message:
            campaign.asset_generation_last_error = error_message

        # Update progress with failure info
        progress = campaign.asset_generation_progress or {}
        progress.update({
            'failed_at': datetime.utcnow().isoformat(),
            'failure_reason': error_message or 'Unknown error'
        })
        campaign.asset_generation_progress = progress

        await session.commit()

