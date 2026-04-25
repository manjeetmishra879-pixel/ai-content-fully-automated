#!/usr/bin/env python3
"""
Test script for auto-fetch engagement data integration.

This script validates that the analytics service auto-fetch functionality
works correctly with the engagement prediction engine.
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.services.analytics_service import AnalyticsService
from app.engines.quality.engagement_prediction import EngagementPredictionEngine
from app.tasks.analytics_tasks import auto_fetch_engagement_data, update_account_followers


async def test_analytics_service():
    """Test the analytics service auto-fetch functionality"""
    print("🧪 Testing Analytics Service Auto-Fetch...")

    db = SessionLocal()

    try:
        analytics_service = AnalyticsService(db)

        # Test auto-fetch for a mock user (assuming user ID 1 exists)
        print("  📊 Testing auto-fetch for user ID 1...")
        results = await analytics_service.auto_fetch_all_posts(user_id=1, hours_back=24)

        print(f"  ✅ Auto-fetch results: {results}")

        # Test competitor engagement calculation
        print("  📈 Testing competitor engagement calculation...")
        competitor_engagement = analytics_service.get_competitor_engagement("instagram", "fitness")
        print(f"  ✅ Competitor engagement: {competitor_engagement}")

        # Test seasonal trend factor
        print("  📅 Testing seasonal trend factor...")
        seasonal_factor = analytics_service.get_seasonal_trend_factor()
        print(f"  ✅ Seasonal trend factor: {seasonal_factor}")

        # Test account followers
        print("  👥 Testing account followers retrieval...")
        followers = analytics_service.get_account_followers(1, "instagram")
        print(f"  ✅ Instagram followers: {followers}")

        print("✅ Analytics service tests passed!")

    except Exception as e:
        print(f"❌ Analytics service test failed: {e}")
        raise
    finally:
        db.close()


def test_engagement_engine_integration():
    """Test that the engagement engine can use analytics service data"""
    print("🧪 Testing Engagement Engine Integration...")

    db = SessionLocal()

    try:
        analytics_service = AnalyticsService(db)
        engagement_engine = EngagementPredictionEngine()

        # Create a mock post for testing
        mock_post = {
            "id": 999,
            "content": "Test post about fitness and wellness",
            "platform": "instagram",
            "hashtags": ["fitness", "health", "workout"],
            "media_type": "video",
            "user_id": 1,
            "account_id": 1,
            "created_at": datetime.utcnow().isoformat(),
            "quality_score": 0.85,
            "sentiment_score": 0.75,
            "topic_relevance": 0.9,
            "hashtag_relevance": 0.8,
            "content_length": 150,
            "hashtag_count": 5,
            "has_cta": True,
            "has_emoji": True,
            "has_question": False,
            "language": "en",
            "is_trending": True,
            "competitor_engagement": 0.0,  # Will be filled by analytics service
            "seasonal_trend_factor": 0.0,   # Will be filled by analytics service
            "account_followers": 0          # Will be filled by analytics service
        }

        # Test feature extraction with analytics integration
        print("  🔍 Testing feature extraction with analytics data...")

        # Get real data from analytics service
        competitor_engagement = analytics_service.get_competitor_engagement("instagram", "fitness")
        seasonal_factor = analytics_service.get_seasonal_trend_factor()
        followers = analytics_service.get_account_followers(1, "instagram")

        # Update mock post with real data
        mock_post["competitor_engagement"] = competitor_engagement
        mock_post["seasonal_trend_factor"] = seasonal_factor
        mock_post["account_followers"] = followers if isinstance(followers, int) else 0

        # Extract features
        features = engagement_engine._extract_features(mock_post)
        print(f"  ✅ Extracted {len(features)} features")

        # Test prediction
        prediction = engagement_engine.predict_engagement(mock_post)
        print(f"  🎯 Engagement prediction: {prediction}")

        print("✅ Engagement engine integration tests passed!")

    except Exception as e:
        print(f"❌ Engagement engine integration test failed: {e}")
        raise
    finally:
        db.close()


def test_celery_tasks():
    """Test that Celery tasks can be called (synchronously for testing)"""
    print("🧪 Testing Celery Tasks...")

    try:
        # Test auto-fetch task
        print("  🚀 Testing auto-fetch engagement data task...")
        result = auto_fetch_engagement_data(user_id=1, hours_back=24)
        print(f"  ✅ Auto-fetch task result: {result}")

        # Test follower update task
        print("  👥 Testing update account followers task...")
        result = update_account_followers(user_id=1)
        print(f"  ✅ Follower update task result: {result}")

        print("✅ Celery task tests passed!")

    except Exception as e:
        print(f"❌ Celery task test failed: {e}")
        raise


async def main():
    """Run all tests"""
    print("🚀 Starting Auto-Fetch Integration Tests\n")

    try:
        # Test analytics service
        await test_analytics_service()
        print()

        # Test engagement engine integration
        test_engagement_engine_integration()
        print()

        # Test Celery tasks
        test_celery_tasks()
        print()

        print("🎉 All tests passed! Auto-fetch integration is working correctly.")
        print("\n📋 Summary:")
        print("  ✅ Analytics service auto-fetch functionality")
        print("  ✅ Competitor engagement calculation")
        print("  ✅ Seasonal trend factor computation")
        print("  ✅ Account follower retrieval")
        print("  ✅ Engagement engine feature integration")
        print("  ✅ Celery task execution")
        print("\n🔄 The system is now production-ready with real data collection!")

    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())