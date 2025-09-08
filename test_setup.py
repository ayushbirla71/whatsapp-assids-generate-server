#!/usr/bin/env python3
"""
Simple test script to verify the asset generation server setup
Run this script to check if all components are working correctly
"""

import asyncio
import os
import sys
import tempfile
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_database_connection():
    """Test database connectivity"""
    print("Testing database connection...")
    try:
        from database import AsyncSessionLocal
        from sqlalchemy import text

        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            if row and row[0] == 1:
                print("✅ Database connection successful")
                return True
            else:
                print("❌ Database connection failed - unexpected result")
                return False
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_s3_configuration():
    """Test S3 configuration"""
    print("Testing S3 configuration...")
    try:
        from s3_uploader import S3Uploader
        s3_uploader = S3Uploader()
        if s3_uploader.s3_client:
            print("✅ S3 client initialized successfully")
            return True
        else:
            print("❌ S3 client initialization failed")
            return False
    except Exception as e:
        print(f"❌ S3 configuration failed: {e}")
        return False

def test_asset_generation_example():
    """Test asset generation example"""
    print("Testing asset generation example...")
    try:
        # Import the sample asset generator
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'examples'))
        import sample_asset_generator
        
        # Test data
        attributes = {
            'greeting': 'Hello',
            'offer': 'Special 50% discount!',
            'product': 'Premium Package',
            'discount': '50%',
            'expiry_date': '31st December 2024'
        }
        name = "John Doe"
        msisdn = "+1234567890"
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate assets
            result = sample_asset_generator.generate_asset(attributes, name, msisdn, temp_dir)
            
            if result and isinstance(result, dict):
                print(f"✅ Asset generation successful - Generated {len(result)} assets:")
                for asset_type, file_path in result.items():
                    if os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        print(f"   - {asset_type}: {os.path.basename(file_path)} ({file_size} bytes)")
                    else:
                        print(f"   - {asset_type}: File not found at {file_path}")
                return True
            else:
                print("❌ Asset generation failed - no result returned")
                return False
                
    except Exception as e:
        print(f"❌ Asset generation test failed: {e}")
        return False

def test_logging_configuration():
    """Test logging configuration"""
    print("Testing logging configuration...")
    try:
        from logger_config import setup_logging, get_logger
        
        # Setup logging
        setup_logging()
        
        # Test logger
        logger = get_logger("test")
        logger.info("Test log message")
        
        # Check if log directory exists
        if os.path.exists("logs"):
            print("✅ Logging configuration successful - logs directory created")
            return True
        else:
            print("❌ Logging configuration failed - logs directory not found")
            return False
            
    except Exception as e:
        print(f"❌ Logging configuration failed: {e}")
        return False

def test_configuration():
    """Test configuration loading"""
    print("Testing configuration...")
    try:
        from config import settings
        
        # Check required settings
        required_settings = [
            'database_url',
            'aws_access_key_id',
            'aws_secret_access_key',
            's3_bucket_name'
        ]
        
        missing_settings = []
        for setting in required_settings:
            if not hasattr(settings, setting) or not getattr(settings, setting):
                missing_settings.append(setting)
        
        if missing_settings:
            print(f"❌ Configuration incomplete - missing: {', '.join(missing_settings)}")
            print("   Please check your .env file")
            return False
        else:
            print("✅ Configuration loaded successfully")
            return True
            
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False

async def test_cron_scheduler():
    """Test cron scheduler initialization"""
    print("Testing cron scheduler...")
    try:
        from cron_scheduler import CronScheduler

        scheduler = CronScheduler()
        print("✅ Cron scheduler initialized successfully")
        return True

    except Exception as e:
        print(f"❌ Cron scheduler test failed: {e}")
        return False

async def test_recovery_manager():
    """Test recovery manager initialization"""
    print("Testing recovery manager...")
    try:
        from recovery_manager import RecoveryManager

        recovery_manager = RecoveryManager()
        print("✅ Recovery manager initialized successfully")
        return True

    except Exception as e:
        print(f"❌ Recovery manager test failed: {e}")
        return False

def test_monitoring_system():
    """Test monitoring system initialization"""
    print("Testing monitoring system...")
    try:
        from monitoring import SystemMonitor

        monitor = SystemMonitor()
        print("✅ Monitoring system initialized successfully")
        return True

    except Exception as e:
        print(f"❌ Monitoring system test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 WhatsApp Asset Generation Server - Setup Test")
    print("=" * 50)
    print(f"Test started at: {datetime.now().isoformat()}")
    print()
    
    tests = [
        ("Configuration", test_configuration),
        ("Logging", test_logging_configuration),
        ("Database Connection", test_database_connection),
        ("S3 Configuration", test_s3_configuration),
        ("Asset Generation Example", test_asset_generation_example),
        ("Cron Scheduler", test_cron_scheduler),
        ("Recovery Manager", test_recovery_manager),
        ("Monitoring System", test_monitoring_system),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your setup is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the configuration and try again.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
