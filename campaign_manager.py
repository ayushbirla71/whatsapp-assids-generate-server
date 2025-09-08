import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from database import (
    AsyncSessionLocal, Campaigns, CampaignAudience, Templates,
    CampaignStatus, AssetGenerationStatus, MessageStatus
)

logger = logging.getLogger(__name__)

class CampaignStatusManager:
    """Manages campaign and audience status updates during asset generation"""

    async def get_campaign_status(self, campaign_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Get detailed status information for a campaign"""
        async with AsyncSessionLocal() as session:
            try:
                # Get campaign details
                campaign = await session.get(Campaigns, campaign_id)
                if not campaign:
                    return None

                # Get audience statistics
                audience_stats = await self._get_audience_statistics(session, campaign_id)
                
                return {
                    "campaign_id": str(campaign_id),
                    "campaign_name": campaign.name,
                    "status": campaign.status.value,
                    "asset_generation_status": campaign.asset_generation_status.value if campaign.asset_generation_status else None,
                    "asset_generation_started_at": campaign.asset_generation_started_at.isoformat() if campaign.asset_generation_started_at else None,
                    "asset_generation_completed_at": campaign.asset_generation_completed_at.isoformat() if campaign.asset_generation_completed_at else None,
                    "audience_statistics": audience_stats,
                    "created_at": campaign.created_at.isoformat(),
                    "updated_at": campaign.updated_at.isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error getting campaign status: {e}", exc_info=True)
                return None

    async def _get_audience_statistics(self, session: AsyncSession, campaign_id: uuid.UUID) -> Dict[str, int]:
        """Get statistics about audience members for a campaign"""
        try:
            # Count total audience members
            total_query = select(func.count(CampaignAudience.id)).where(
                CampaignAudience.campaign_id == campaign_id
            )
            total_result = await session.execute(total_query)
            total_count = total_result.scalar() or 0

            # Count by message status
            status_query = select(
                CampaignAudience.message_status,
                func.count(CampaignAudience.id)
            ).where(
                CampaignAudience.campaign_id == campaign_id
            ).group_by(CampaignAudience.message_status)
            
            status_result = await session.execute(status_query)
            status_counts = {status.value: 0 for status in MessageStatus}
            
            for status, count in status_result:
                if status:
                    status_counts[status.value] = count

            # Count by asset generation status
            asset_query = select(
                CampaignAudience.asset_generation_status,
                func.count(CampaignAudience.id)
            ).where(
                CampaignAudience.campaign_id == campaign_id
            ).group_by(CampaignAudience.asset_generation_status)
            
            asset_result = await session.execute(asset_query)
            asset_counts = {status.value: 0 for status in AssetGenerationStatus}
            asset_counts["none"] = 0  # For null values
            
            for status, count in asset_result:
                if status:
                    asset_counts[status.value] = count
                else:
                    asset_counts["none"] = count

            return {
                "total_audience": total_count,
                "message_status_counts": status_counts,
                "asset_generation_status_counts": asset_counts
            }
            
        except Exception as e:
            logger.error(f"Error getting audience statistics: {e}", exc_info=True)
            return {
                "total_audience": 0,
                "message_status_counts": {},
                "asset_generation_status_counts": {}
            }

    async def update_campaign_status(
        self, 
        campaign_id: uuid.UUID, 
        status: CampaignStatus,
        asset_generation_status: Optional[AssetGenerationStatus] = None
    ) -> bool:
        """Update campaign status"""
        async with AsyncSessionLocal() as session:
            try:
                campaign = await session.get(Campaigns, campaign_id)
                if not campaign:
                    logger.error(f"Campaign {campaign_id} not found")
                    return False

                campaign.status = status
                campaign.updated_at = datetime.utcnow()
                
                if asset_generation_status:
                    campaign.asset_generation_status = asset_generation_status
                    
                    if asset_generation_status == AssetGenerationStatus.PROCESSING:
                        campaign.asset_generation_started_at = datetime.utcnow()
                    elif asset_generation_status in [AssetGenerationStatus.GENERATED, AssetGenerationStatus.FAILED]:
                        campaign.asset_generation_completed_at = datetime.utcnow()

                await session.commit()
                logger.info(f"Updated campaign {campaign_id} status to {status.value}")
                return True
                
            except Exception as e:
                logger.error(f"Error updating campaign status: {e}", exc_info=True)
                await session.rollback()
                return False

    async def update_audience_member_status(
        self,
        audience_id: uuid.UUID,
        message_status: Optional[MessageStatus] = None,
        asset_generation_status: Optional[AssetGenerationStatus] = None,
        asset_urls: Optional[Dict[str, str]] = None
    ) -> bool:
        """Update audience member status"""
        async with AsyncSessionLocal() as session:
            try:
                audience_member = await session.get(CampaignAudience, audience_id)
                if not audience_member:
                    logger.error(f"Audience member {audience_id} not found")
                    return False

                if message_status:
                    audience_member.message_status = message_status
                    
                if asset_generation_status:
                    audience_member.asset_generation_status = asset_generation_status
                    
                if asset_urls:
                    audience_member.generated_asset_urls = asset_urls

                audience_member.updated_at = datetime.utcnow()
                await session.commit()
                
                logger.info(f"Updated audience member {audience_id} status")
                return True
                
            except Exception as e:
                logger.error(f"Error updating audience member status: {e}", exc_info=True)
                await session.rollback()
                return False

    async def get_campaigns_by_status(self, status: CampaignStatus) -> List[Dict[str, Any]]:
        """Get all campaigns with a specific status"""
        async with AsyncSessionLocal() as session:
            try:
                query = select(Campaigns).where(Campaigns.status == status)
                result = await session.execute(query)
                campaigns = result.scalars().all()
                
                campaign_list = []
                for campaign in campaigns:
                    campaign_data = {
                        "id": str(campaign.id),
                        "name": campaign.name,
                        "description": campaign.description,
                        "status": campaign.status.value,
                        "asset_generation_status": campaign.asset_generation_status.value if campaign.asset_generation_status else None,
                        "created_at": campaign.created_at.isoformat(),
                        "updated_at": campaign.updated_at.isoformat()
                    }
                    campaign_list.append(campaign_data)
                
                return campaign_list
                
            except Exception as e:
                logger.error(f"Error getting campaigns by status: {e}", exc_info=True)
                return []

    async def get_audience_members_by_status(
        self, 
        campaign_id: uuid.UUID, 
        message_status: Optional[MessageStatus] = None,
        asset_generation_status: Optional[AssetGenerationStatus] = None
    ) -> List[Dict[str, Any]]:
        """Get audience members filtered by status"""
        async with AsyncSessionLocal() as session:
            try:
                query = select(CampaignAudience).where(CampaignAudience.campaign_id == campaign_id)
                
                if message_status:
                    query = query.where(CampaignAudience.message_status == message_status)
                    
                if asset_generation_status:
                    query = query.where(CampaignAudience.asset_generation_status == asset_generation_status)
                
                result = await session.execute(query)
                audience_members = result.scalars().all()
                
                member_list = []
                for member in audience_members:
                    member_data = {
                        "id": str(member.id),
                        "name": member.name,
                        "msisdn": member.msisdn,
                        "message_status": member.message_status.value,
                        "asset_generation_status": member.asset_generation_status.value if member.asset_generation_status else None,
                        "generated_asset_urls": member.generated_asset_urls or {},
                        "attributes": member.attributes or {},
                        "created_at": member.created_at.isoformat(),
                        "updated_at": member.updated_at.isoformat()
                    }
                    member_list.append(member_data)
                
                return member_list
                
            except Exception as e:
                logger.error(f"Error getting audience members by status: {e}", exc_info=True)
                return []

    async def check_campaign_completion(self, campaign_id: uuid.UUID) -> bool:
        """Check if all audience members have completed asset generation"""
        async with AsyncSessionLocal() as session:
            try:
                # Count total audience members
                total_query = select(func.count(CampaignAudience.id)).where(
                    CampaignAudience.campaign_id == campaign_id
                )
                total_result = await session.execute(total_query)
                total_count = total_result.scalar() or 0

                # Count completed (generated or failed) audience members
                completed_query = select(func.count(CampaignAudience.id)).where(
                    and_(
                        CampaignAudience.campaign_id == campaign_id,
                        CampaignAudience.asset_generation_status.in_([
                            AssetGenerationStatus.GENERATED,
                            AssetGenerationStatus.FAILED
                        ])
                    )
                )
                completed_result = await session.execute(completed_query)
                completed_count = completed_result.scalar() or 0

                return total_count > 0 and completed_count == total_count
                
            except Exception as e:
                logger.error(f"Error checking campaign completion: {e}", exc_info=True)
                return False
