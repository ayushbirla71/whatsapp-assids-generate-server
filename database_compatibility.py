"""
Database compatibility checker for WhatsApp Asset Generation Server
Checks if the required columns exist before using them
"""

import asyncio
import logging
from sqlalchemy import text
from database import AsyncSessionLocal

logger = logging.getLogger(__name__)

class DatabaseCompatibility:
    def __init__(self):
        self.asset_generation_columns_exist = False
        self.checked = False
    
    async def check_compatibility(self):
        """Check if the asset generation columns exist in the database"""
        if self.checked:
            return self.asset_generation_columns_exist
            
        async with AsyncSessionLocal() as session:
            try:
                # Check if asset generation columns exist in campaigns table
                query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'campaigns' 
                    AND column_name IN ('asset_generation_status', 'asset_generation_started_at', 'asset_generation_completed_at')
                """)
                
                result = await session.execute(query)
                columns = [row[0] for row in result.fetchall()]
                
                # Check if all required columns exist
                required_columns = ['asset_generation_status', 'asset_generation_started_at', 'asset_generation_completed_at']
                self.asset_generation_columns_exist = all(col in columns for col in required_columns)
                
                if self.asset_generation_columns_exist:
                    logger.info("✅ Asset generation columns found in database")
                else:
                    logger.warning("⚠️ Asset generation columns not found. Please run the migration script.")
                    logger.info("Missing columns: " + ", ".join([col for col in required_columns if col not in columns]))
                
                self.checked = True
                return self.asset_generation_columns_exist
                
            except Exception as e:
                logger.error(f"Error checking database compatibility: {e}")
                self.checked = True
                self.asset_generation_columns_exist = False
                return False
    
    async def get_campaigns_safely(self):
        """Get campaigns using safe queries that work with or without new columns"""
        async with AsyncSessionLocal() as session:
            try:
                if await self.check_compatibility():
                    # Use full query with asset generation columns
                    query = text("""
                        SELECT id, name, status, asset_generation_status 
                        FROM campaigns 
                        WHERE status = 'approved'
                    """)
                else:
                    # Use basic query without asset generation columns
                    query = text("""
                        SELECT id, name, status 
                        FROM campaigns 
                        WHERE status = 'approved'
                    """)
                
                result = await session.execute(query)
                return result.fetchall()
                
            except Exception as e:
                logger.error(f"Error getting campaigns safely: {e}")
                return []

# Global instance
db_compatibility = DatabaseCompatibility()

async def check_database_compatibility():
    """Check database compatibility and return status"""
    return await db_compatibility.check_compatibility()

async def get_approved_campaigns_safely():
    """Get approved campaigns using compatibility-safe queries"""
    return await db_compatibility.get_campaigns_safely()
