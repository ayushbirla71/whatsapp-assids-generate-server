from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import uuid

from campaign_manager import CampaignStatusManager
from recovery_manager import RecoveryManager
from monitoring import SystemMonitor
from database import CampaignStatus, MessageStatus, AssetGenerationStatus
from logger_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Asset Generation"])

# Initialize managers
campaign_manager = CampaignStatusManager()
recovery_manager = RecoveryManager()
system_monitor = SystemMonitor()

@router.get("/campaigns/{campaign_id}/status")
async def get_campaign_status(campaign_id: uuid.UUID):
    """Get detailed status of a campaign"""
    try:
        status = await campaign_manager.get_campaign_status(campaign_id)
        if not status:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return status
    except Exception as e:
        logger.error(f"Error getting campaign status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/campaigns/status/{status}")
async def get_campaigns_by_status(status: str):
    """Get all campaigns with a specific status"""
    try:
        # Validate status
        try:
            campaign_status = CampaignStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        campaigns = await campaign_manager.get_campaigns_by_status(campaign_status)
        return {"campaigns": campaigns, "count": len(campaigns)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaigns by status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/campaigns/{campaign_id}/audience")
async def get_campaign_audience(
    campaign_id: uuid.UUID,
    message_status: Optional[str] = None,
    asset_generation_status: Optional[str] = None
):
    """Get audience members for a campaign, optionally filtered by status"""
    try:
        # Validate status parameters
        msg_status = None
        if message_status:
            try:
                msg_status = MessageStatus(message_status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid message status: {message_status}")
        
        asset_status = None
        if asset_generation_status:
            try:
                asset_status = AssetGenerationStatus(asset_generation_status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid asset generation status: {asset_generation_status}")
        
        audience_members = await campaign_manager.get_audience_members_by_status(
            campaign_id, msg_status, asset_status
        )
        return {"audience_members": audience_members, "count": len(audience_members)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign audience: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/campaigns/{campaign_id}/status")
async def update_campaign_status(
    campaign_id: uuid.UUID,
    status: str,
    asset_generation_status: Optional[str] = None
):
    """Update campaign status"""
    try:
        # Validate status
        try:
            campaign_status = CampaignStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        asset_status = None
        if asset_generation_status:
            try:
                asset_status = AssetGenerationStatus(asset_generation_status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid asset generation status: {asset_generation_status}")
        
        success = await campaign_manager.update_campaign_status(
            campaign_id, campaign_status, asset_status
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Campaign not found or update failed")
        
        return {"message": "Campaign status updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating campaign status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health/detailed")
async def detailed_health_check():
    """Comprehensive system health check"""
    try:
        health_data = await system_monitor.get_system_health()

        # Determine HTTP status code based on health
        status_code = 200
        if health_data.get('overall_status') == 'critical':
            status_code = 503
        elif health_data.get('overall_status') == 'degraded':
            status_code = 206  # Partial Content

        return health_data

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Service unhealthy")

@router.get("/monitoring/stuck-processes")
async def get_stuck_processes():
    """Get report of stuck processes"""
    try:
        report = await system_monitor.get_stuck_processes_report()
        return report
    except Exception as e:
        logger.error(f"Error getting stuck processes report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/recovery/startup")
async def trigger_startup_recovery():
    """Manually trigger startup recovery process"""
    try:
        await recovery_manager.perform_startup_recovery()
        return {"message": "Startup recovery completed successfully"}
    except Exception as e:
        logger.error(f"Error in manual startup recovery: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Recovery failed")

@router.post("/recovery/runtime")
async def trigger_runtime_recovery():
    """Manually trigger runtime recovery check"""
    try:
        await recovery_manager.check_and_recover_during_runtime()
        return {"message": "Runtime recovery check completed successfully"}
    except Exception as e:
        logger.error(f"Error in manual runtime recovery: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Recovery failed")

@router.get("/recovery/statistics")
async def get_recovery_statistics():
    """Get recovery operation statistics"""
    try:
        stats = await recovery_manager.get_recovery_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting recovery statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/stats/overview")
async def get_system_overview():
    """Get system overview statistics"""
    try:
        # Get counts for different campaign statuses
        stats = {}
        for status in CampaignStatus:
            campaigns = await campaign_manager.get_campaigns_by_status(status)
            stats[f"campaigns_{status.value}"] = len(campaigns)
        
        return {
            "statistics": stats,
            "timestamp": "2024-01-01T00:00:00Z"  # This would be actual timestamp
        }
    except Exception as e:
        logger.error(f"Error getting system overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
