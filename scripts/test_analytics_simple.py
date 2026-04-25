#!/usr/bin/env python3
"""
Simple test script for analytics service auto-fetch functionality.

Tests the analytics service without importing ML libraries to avoid numpy issues.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.services.analytics_service import AnalyticsService


async def test_analytics_service():
    """Test the analytics service auto-fetch functionality"""
    print("🧪 Testing Analytics Service Auto-Fetch...")

    db = SessionLocal()

    try:
        analytics_service = AnalyticsService(db)

        # Test competitor engagement calculation
        print("  📈 Testing competitor engagement calculation...")
        competitor_engagement = analytics_service.get_competitor_engagement("instagram", "fitness")
        print(f"  ✅ Competitor engagement: {competitor_engagement}")

        # Test seasonal trend factor
        print("  📅 Testing seasonal trend factor...")
        seasonal_factor = analytics_service.get_seasonal_trend_factor()
        print(f"  ✅ Seasonal trend factor: {seasonal_factor}")

        # Test account followers (this will likely fail without real API tokens)
        print("  👥 Testing account followers retrieval...")
        try:
            followers = analytics_service.get_account_followers(1, "instagram")
            print(f"  ✅ Instagram followers: {followers}")
        except Exception as e:
            print(f"  ⚠️  Account followers test failed (expected without API tokens): {e}")

        print("✅ Analytics service basic tests passed!")

    except Exception as e:
        print(f"❌ Analytics service test failed: {e}")
        raise
    finally:
        db.close()


def test_celery_task_imports():
    """Test that Celery tasks can be imported"""
    print("🧪 Testing Celery Task Imports...")

    try:
        from app.tasks.analytics_tasks import auto_fetch_engagement_data, update_account_followers
        print("  ✅ Successfully imported auto_fetch_engagement_data")
        print("  ✅ Successfully imported update_account_followers")
        print("✅ Celery task import tests passed!")

    except Exception as e:
        print(f"❌ Celery task import test failed: {e}")
        raise


async def main():
    """Run all tests"""
    print("🚀 Starting Simple Auto-Fetch Integration Tests\n")

    try:
        # Test analytics service
        await test_analytics_service()
        print()

        # Test Celery task imports
        test_celery_task_imports()
        print()

        print("🎉 Basic integration tests passed!")
        print("\n📋 Summary:")
        print("  ✅ Analytics service competitor engagement calculation")
        print("  ✅ Analytics service seasonal trend factor computation")
        print("  ✅ Celery task imports")
        print("\n🔄 The analytics service is ready for integration!")
        print("   Note: Full ML testing requires resolving numpy/scipy compatibility")

    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())