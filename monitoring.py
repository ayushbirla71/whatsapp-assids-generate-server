import asyncio
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database import (
    AsyncSessionLocal, Campaigns, CampaignAudience,
    CampaignStatus, AssetGenerationStatus, MessageStatus
)
from logger_config import get_logger
from config import settings

logger = get_logger(__name__)

class SystemMonitor:
    """Comprehensive system monitoring for asset generation server"""
    
    def __init__(self):
        self.start_time = time.time()
        self.generation_stats = {
            'total_campaigns_processed': 0,
            'total_assets_generated': 0,
            'total_failures': 0,
            'average_generation_time': 0
        }

    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health information"""
        try:
            health_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'uptime_seconds': time.time() - self.start_time,
                'system_resources': self._get_system_resources(),
                'database_health': await self._check_database_health(),
                's3_health': await self._check_s3_health(),
                'asset_generation_stats': await self._get_asset_generation_stats(),
                'campaign_status_summary': await self._get_campaign_status_summary(),
                'error_summary': await self._get_error_summary(),
                'performance_metrics': await self._get_performance_metrics()
            }
            
            # Determine overall health status
            health_data['overall_status'] = self._determine_overall_health(health_data)
            
            return health_data
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}", exc_info=True)
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'overall_status': 'unhealthy',
                'error': str(e)
            }

    def _get_system_resources(self) -> Dict[str, Any]:
        """Get system resource usage"""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
                'process_count': len(psutil.pids())
            }
        except Exception as e:
            logger.error(f"Error getting system resources: {e}")
            return {'error': str(e)}

    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        try:
            start_time = time.time()
            
            async with AsyncSessionLocal() as session:
                # Test basic connectivity
                await session.execute("SELECT 1")
                
                # Test table access
                result = await session.execute(
                    select(func.count(Campaigns.id))
                )
                campaign_count = result.scalar()
                
                response_time = time.time() - start_time
                
                return {
                    'status': 'healthy',
                    'response_time_ms': round(response_time * 1000, 2),
                    'total_campaigns': campaign_count
                }
                
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }

    async def _check_s3_health(self) -> Dict[str, Any]:
        """Check S3 connectivity"""
        try:
            from s3_uploader import S3Uploader
            s3_uploader = S3Uploader()
            
            # Simple S3 connectivity test
            if s3_uploader.s3_client:
                return {
                    'status': 'healthy',
                    'bucket': settings.s3_bucket_name,
                    'region': settings.aws_region
                }
            else:
                return {
                    'status': 'unhealthy',
                    'error': 'S3 client not initialized'
                }
                
        except Exception as e:
            logger.error(f"S3 health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }

    async def _get_asset_generation_stats(self) -> Dict[str, Any]:
        """Get asset generation statistics"""
        async with AsyncSessionLocal() as session:
            try:
                # Get stats for the last 24 hours
                since = datetime.utcnow() - timedelta(hours=24)
                
                # Total campaigns processed
                campaigns_query = select(func.count(Campaigns.id)).where(
                    and_(
                        Campaigns.asset_generation_started_at >= since,
                        Campaigns.asset_generation_status.isnot(None)
                    )
                )
                campaigns_result = await session.execute(campaigns_query)
                campaigns_processed = campaigns_result.scalar() or 0

                # Total assets generated
                assets_query = select(func.count(CampaignAudience.id)).where(
                    and_(
                        CampaignAudience.asset_generation_completed_at >= since,
                        CampaignAudience.asset_generation_status == AssetGenerationStatus.GENERATED
                    )
                )
                assets_result = await session.execute(assets_query)
                assets_generated = assets_result.scalar() or 0

                # Total failures
                failures_query = select(func.count(CampaignAudience.id)).where(
                    and_(
                        CampaignAudience.asset_generation_completed_at >= since,
                        CampaignAudience.asset_generation_status == AssetGenerationStatus.FAILED
                    )
                )
                failures_result = await session.execute(failures_query)
                total_failures = failures_result.scalar() or 0

                # Currently processing
                processing_query = select(func.count(CampaignAudience.id)).where(
                    CampaignAudience.asset_generation_status == AssetGenerationStatus.PROCESSING
                )
                processing_result = await session.execute(processing_query)
                currently_processing = processing_result.scalar() or 0

                return {
                    'last_24_hours': {
                        'campaigns_processed': campaigns_processed,
                        'assets_generated': assets_generated,
                        'failures': total_failures,
                        'success_rate': round((assets_generated / max(assets_generated + total_failures, 1)) * 100, 2)
                    },
                    'currently_processing': currently_processing
                }
                
            except Exception as e:
                logger.error(f"Error getting asset generation stats: {e}")
                return {'error': str(e)}

    async def _get_campaign_status_summary(self) -> Dict[str, int]:
        """Get summary of campaign statuses"""
        async with AsyncSessionLocal() as session:
            try:
                summary = {}
                
                for status in CampaignStatus:
                    query = select(func.count(Campaigns.id)).where(
                        Campaigns.status == status
                    )
                    result = await session.execute(query)
                    count = result.scalar() or 0
                    summary[status.value] = count
                
                return summary
                
            except Exception as e:
                logger.error(f"Error getting campaign status summary: {e}")
                return {}

    async def _get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors"""
        async with AsyncSessionLocal() as session:
            try:
                since = datetime.utcnow() - timedelta(hours=24)
                
                # Campaign errors
                campaign_errors_query = select(
                    Campaigns.asset_generation_last_error,
                    func.count(Campaigns.id)
                ).where(
                    and_(
                        Campaigns.asset_generation_last_error.isnot(None),
                        Campaigns.updated_at >= since
                    )
                ).group_by(Campaigns.asset_generation_last_error)
                
                campaign_errors_result = await session.execute(campaign_errors_query)
                campaign_errors = dict(campaign_errors_result.fetchall())

                # Audience errors
                audience_errors_query = select(
                    CampaignAudience.asset_generation_last_error,
                    func.count(CampaignAudience.id)
                ).where(
                    and_(
                        CampaignAudience.asset_generation_last_error.isnot(None),
                        CampaignAudience.updated_at >= since
                    )
                ).group_by(CampaignAudience.asset_generation_last_error)
                
                audience_errors_result = await session.execute(audience_errors_query)
                audience_errors = dict(audience_errors_result.fetchall())

                return {
                    'campaign_errors': campaign_errors,
                    'audience_errors': audience_errors,
                    'total_campaign_errors': sum(campaign_errors.values()),
                    'total_audience_errors': sum(audience_errors.values())
                }
                
            except Exception as e:
                logger.error(f"Error getting error summary: {e}")
                return {}

    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        async with AsyncSessionLocal() as session:
            try:
                since = datetime.utcnow() - timedelta(hours=24)
                
                # Average generation time for successful generations
                avg_time_query = select(
                    func.avg(
                        func.extract('epoch', CampaignAudience.asset_generation_completed_at) -
                        func.extract('epoch', CampaignAudience.asset_generation_started_at)
                    )
                ).where(
                    and_(
                        CampaignAudience.asset_generation_started_at >= since,
                        CampaignAudience.asset_generation_status == AssetGenerationStatus.GENERATED,
                        CampaignAudience.asset_generation_started_at.isnot(None),
                        CampaignAudience.asset_generation_completed_at.isnot(None)
                    )
                )
                
                avg_time_result = await session.execute(avg_time_query)
                avg_generation_time = avg_time_result.scalar()

                # Retry statistics
                retry_stats_query = select(
                    CampaignAudience.asset_generation_retry_count,
                    func.count(CampaignAudience.id)
                ).where(
                    CampaignAudience.asset_generation_retry_count > 0
                ).group_by(CampaignAudience.asset_generation_retry_count)
                
                retry_stats_result = await session.execute(retry_stats_query)
                retry_stats = dict(retry_stats_result.fetchall())

                return {
                    'average_generation_time_seconds': round(avg_generation_time or 0, 2),
                    'retry_statistics': retry_stats,
                    'total_retries': sum(retry_stats.values())
                }
                
            except Exception as e:
                logger.error(f"Error getting performance metrics: {e}")
                return {}

    def _determine_overall_health(self, health_data: Dict[str, Any]) -> str:
        """Determine overall system health status"""
        try:
            # Check critical components
            if health_data.get('database_health', {}).get('status') != 'healthy':
                return 'critical'
            
            if health_data.get('s3_health', {}).get('status') != 'healthy':
                return 'degraded'
            
            # Check system resources
            resources = health_data.get('system_resources', {})
            if resources.get('cpu_percent', 0) > 90 or resources.get('memory_percent', 0) > 90:
                return 'degraded'
            
            # Check error rates
            error_summary = health_data.get('error_summary', {})
            total_errors = error_summary.get('total_campaign_errors', 0) + error_summary.get('total_audience_errors', 0)
            if total_errors > 100:  # More than 100 errors in 24 hours
                return 'degraded'
            
            return 'healthy'
            
        except Exception as e:
            logger.error(f"Error determining overall health: {e}")
            return 'unknown'

    async def get_stuck_processes_report(self) -> Dict[str, Any]:
        """Get report of potentially stuck processes"""
        async with AsyncSessionLocal() as session:
            try:
                cutoff_time = datetime.utcnow() - timedelta(minutes=30)
                
                # Find stuck campaigns
                stuck_campaigns_query = select(Campaigns).where(
                    and_(
                        Campaigns.status == CampaignStatus.ASSET_GENERATION,
                        Campaigns.asset_generation_status == AssetGenerationStatus.PROCESSING,
                        Campaigns.asset_generation_started_at < cutoff_time
                    )
                )
                stuck_campaigns_result = await session.execute(stuck_campaigns_query)
                stuck_campaigns = stuck_campaigns_result.scalars().all()

                # Find stuck audience members
                stuck_audience_query = select(CampaignAudience).where(
                    and_(
                        CampaignAudience.message_status == MessageStatus.ASSET_GENERATING,
                        CampaignAudience.asset_generation_status == AssetGenerationStatus.PROCESSING,
                        CampaignAudience.asset_generation_started_at < cutoff_time
                    )
                )
                stuck_audience_result = await session.execute(stuck_audience_query)
                stuck_audience = stuck_audience_result.scalars().all()

                return {
                    'stuck_campaigns': [
                        {
                            'id': str(campaign.id),
                            'name': campaign.name,
                            'started_at': campaign.asset_generation_started_at.isoformat() if campaign.asset_generation_started_at else None,
                            'retry_count': campaign.asset_generation_retry_count
                        }
                        for campaign in stuck_campaigns
                    ],
                    'stuck_audience_members': [
                        {
                            'id': str(member.id),
                            'name': member.name,
                            'campaign_id': str(member.campaign_id),
                            'started_at': member.asset_generation_started_at.isoformat() if member.asset_generation_started_at else None,
                            'retry_count': member.asset_generation_retry_count
                        }
                        for member in stuck_audience
                    ],
                    'total_stuck_campaigns': len(stuck_campaigns),
                    'total_stuck_audience': len(stuck_audience)
                }
                
            except Exception as e:
                logger.error(f"Error getting stuck processes report: {e}")
                return {'error': str(e)}
