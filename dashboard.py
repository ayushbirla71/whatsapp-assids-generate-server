#!/usr/bin/env python3
"""
Simple command-line dashboard for monitoring the asset generation server
Run this script to get a real-time view of the system status
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any

import aiohttp

class AssetGenerationDashboard:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_system_health(self) -> Dict[str, Any]:
        """Get system health information"""
        try:
            async with self.session.get(f"{self.base_url}/api/v1/health/detailed") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}

    async def get_stuck_processes(self) -> Dict[str, Any]:
        """Get stuck processes report"""
        try:
            async with self.session.get(f"{self.base_url}/api/v1/monitoring/stuck-processes") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}

    async def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery statistics"""
        try:
            async with self.session.get(f"{self.base_url}/api/v1/recovery/statistics") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}

    def format_health_status(self, health_data: Dict[str, Any]) -> str:
        """Format health status for display"""
        if "error" in health_data:
            return f"❌ ERROR: {health_data['error']}"

        status = health_data.get('overall_status', 'unknown')
        status_icons = {
            'healthy': '✅',
            'degraded': '⚠️',
            'critical': '❌',
            'unknown': '❓'
        }

        lines = [
            f"{status_icons.get(status, '❓')} Overall Status: {status.upper()}",
            f"🕐 Uptime: {self.format_uptime(health_data.get('uptime_seconds', 0))}",
            ""
        ]

        # System resources
        resources = health_data.get('system_resources', {})
        if resources and 'error' not in resources:
            lines.extend([
                "💻 System Resources:",
                f"   CPU: {resources.get('cpu_percent', 0):.1f}%",
                f"   Memory: {resources.get('memory_percent', 0):.1f}%",
                f"   Disk: {resources.get('disk_percent', 0):.1f}%",
                ""
            ])

        # Database health
        db_health = health_data.get('database_health', {})
        db_status = "✅" if db_health.get('status') == 'healthy' else "❌"
        lines.append(f"{db_status} Database: {db_health.get('status', 'unknown')}")

        # S3 health
        s3_health = health_data.get('s3_health', {})
        s3_status = "✅" if s3_health.get('status') == 'healthy' else "❌"
        lines.append(f"{s3_status} S3: {s3_health.get('status', 'unknown')}")

        lines.append("")

        # Asset generation stats
        asset_stats = health_data.get('asset_generation_stats', {})
        if asset_stats and 'error' not in asset_stats:
            last_24h = asset_stats.get('last_24_hours', {})
            lines.extend([
                "📊 Asset Generation (Last 24h):",
                f"   Campaigns: {last_24h.get('campaigns_processed', 0)}",
                f"   Assets: {last_24h.get('assets_generated', 0)}",
                f"   Failures: {last_24h.get('failures', 0)}",
                f"   Success Rate: {last_24h.get('success_rate', 0):.1f}%",
                f"   Currently Processing: {asset_stats.get('currently_processing', 0)}",
                ""
            ])

        # Campaign status summary
        campaign_summary = health_data.get('campaign_status_summary', {})
        if campaign_summary:
            lines.extend([
                "📋 Campaign Status Summary:",
                f"   Approved: {campaign_summary.get('approved', 0)}",
                f"   Asset Generation: {campaign_summary.get('asset_generation', 0)}",
                f"   Asset Generated: {campaign_summary.get('asset_generated', 0)}",
                f"   Ready to Launch: {campaign_summary.get('ready_to_launch', 0)}",
                ""
            ])

        return "\n".join(lines)

    def format_stuck_processes(self, stuck_data: Dict[str, Any]) -> str:
        """Format stuck processes for display"""
        if "error" in stuck_data:
            return f"❌ ERROR: {stuck_data['error']}"

        lines = [
            "🔄 Stuck Processes Report:",
            f"   Stuck Campaigns: {stuck_data.get('total_stuck_campaigns', 0)}",
            f"   Stuck Audience Members: {stuck_data.get('total_stuck_audience', 0)}",
            ""
        ]

        # Show details of stuck campaigns
        stuck_campaigns = stuck_data.get('stuck_campaigns', [])
        if stuck_campaigns:
            lines.append("📋 Stuck Campaigns:")
            for campaign in stuck_campaigns[:5]:  # Show first 5
                lines.append(f"   - {campaign.get('name', 'Unknown')} (Retries: {campaign.get('retry_count', 0)})")
            if len(stuck_campaigns) > 5:
                lines.append(f"   ... and {len(stuck_campaigns) - 5} more")
            lines.append("")

        return "\n".join(lines)

    def format_recovery_stats(self, recovery_data: Dict[str, Any]) -> str:
        """Format recovery statistics for display"""
        if "error" in recovery_data:
            return f"❌ ERROR: {recovery_data['error']}"

        lines = [
            "🔧 Recovery Statistics:",
            f"   Campaigns Recovered: {recovery_data.get('campaigns_recovered', 0)}",
            f"   Audience Members Recovered: {recovery_data.get('audience_members_recovered', 0)}",
            f"   Max Retry Count: {recovery_data.get('max_retry_count', 0)}",
            f"   Stuck Timeout: {recovery_data.get('stuck_timeout_minutes', 0)} minutes",
            ""
        ]

        return "\n".join(lines)

    def format_uptime(self, seconds: float) -> str:
        """Format uptime in human readable format"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        elif seconds < 86400:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
        else:
            days = int(seconds // 86400)
            hours = int((seconds % 86400) // 3600)
            return f"{days}d {hours}h"

    async def display_dashboard(self, refresh_interval: int = 30):
        """Display the dashboard with auto-refresh"""
        try:
            while True:
                # Clear screen
                print("\033[2J\033[H", end="")
                
                # Header
                print("=" * 80)
                print("🚀 WhatsApp Asset Generation Server - Dashboard")
                print("=" * 80)
                print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"🔄 Auto-refresh every {refresh_interval} seconds (Ctrl+C to exit)")
                print("=" * 80)
                print()

                # Get data
                health_data = await self.get_system_health()
                stuck_data = await self.get_stuck_processes()
                recovery_data = await self.get_recovery_stats()

                # Display sections
                print(self.format_health_status(health_data))
                print(self.format_stuck_processes(stuck_data))
                print(self.format_recovery_stats(recovery_data))

                print("=" * 80)
                print("💡 Tip: Use the API endpoints for more detailed information")
                print("   GET /api/v1/health/detailed")
                print("   GET /api/v1/monitoring/stuck-processes")
                print("   POST /api/v1/recovery/startup")

                # Wait for next refresh
                await asyncio.sleep(refresh_interval)

        except KeyboardInterrupt:
            print("\n\n👋 Dashboard stopped by user")
        except Exception as e:
            print(f"\n\n❌ Dashboard error: {e}")

async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Asset Generation Server Dashboard")
    parser.add_argument("--url", default="http://localhost:8000", help="Server URL")
    parser.add_argument("--refresh", type=int, default=30, help="Refresh interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    
    args = parser.parse_args()

    async with AssetGenerationDashboard(args.url) as dashboard:
        if args.once:
            # Single run
            print("🚀 WhatsApp Asset Generation Server - Status")
            print("=" * 60)
            
            health_data = await dashboard.get_system_health()
            stuck_data = await dashboard.get_stuck_processes()
            recovery_data = await dashboard.get_recovery_stats()
            
            print(dashboard.format_health_status(health_data))
            print(dashboard.format_stuck_processes(stuck_data))
            print(dashboard.format_recovery_stats(recovery_data))
        else:
            # Continuous dashboard
            await dashboard.display_dashboard(args.refresh)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
