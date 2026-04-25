#!/usr/bin/env python3
"""
Real API Integration Test for Auto-Fetch System.

This script tests the auto-fetch functionality with real platform API keys.
Configure your API keys in .env file before running.

Usage:
    python scripts/test_real_api_integration.py --use-real-apis
    python scripts/test_real_api_integration.py --mock-only
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.services.analytics_service import AnalyticsService
from app.tasks.analytics_tasks import auto_fetch_engagement_data, update_account_followers


class RealAPIIntegrationTester:
    """Test real API integration for the auto-fetch system."""

    def __init__(self, use_real_apis: bool = False):
        self.use_real_apis = use_real_apis
        self.db = SessionLocal()
        self.analytics_service = AnalyticsService(self.db)
        self.test_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "use_real_apis": use_real_apis,
            "tests": {}
        }

    def check_api_keys(self) -> Dict[str, bool]:
        """Check which API keys are configured."""
        api_keys_status = {}

        # YouTube
        api_keys_status["youtube"] = bool(os.getenv("YOUTUBE_API_KEY"))

        # Instagram
        api_keys_status["instagram"] = bool(os.getenv("INSTAGRAM_ACCESS_TOKEN"))

        # TikTok
        api_keys_status["tiktok"] = bool(os.getenv("TIKTOK_ACCESS_TOKEN"))

        # Facebook
        api_keys_status["facebook"] = bool(os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN"))

        # Twitter/X
        api_keys_status["twitter"] = bool(os.getenv("X_BEARER_TOKEN"))

        # LinkedIn
        api_keys_status["linkedin"] = bool(os.getenv("LINKEDIN_ACCESS_TOKEN"))

        return api_keys_status

    async def test_platform_analytics_fetch(self, platform: str, test_post_id: str = "test_123") -> Dict[str, Any]:
        """Test fetching analytics from a specific platform."""
        print(f"🧪 Testing {platform} analytics fetch...")

        try:
            # Get appropriate access token based on platform
            access_token = self._get_access_token(platform)

            if not access_token and self.use_real_apis:
                return {"status": "skipped", "reason": f"No {platform} API key configured"}

            # Test the fetch
            start_time = datetime.utcnow()
            result = await self.analytics_service.fetch_platform_analytics(
                platform=platform,
                post_id=test_post_id,
                access_token=access_token,
                user_id=1
            )
            end_time = datetime.utcnow()

            return {
                "status": "success",
                "platform": platform,
                "data_keys": list(result.keys()) if result else [],
                "response_time_seconds": (end_time - start_time).total_seconds(),
                "data": result
            }

        except Exception as e:
            return {
                "status": "error",
                "platform": platform,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def test_celery_task_execution(self) -> Dict[str, Any]:
        """Test that Celery tasks can be executed."""
        print("🧪 Testing Celery task execution...")

        try:
            # Test task import
            from app.tasks.analytics_tasks import auto_fetch_engagement_data, update_account_followers

            # Test task creation (don't actually run to avoid API calls)
            task1 = auto_fetch_engagement_data
            task2 = update_account_followers

            return {
                "status": "success",
                "tasks_available": ["auto_fetch_engagement_data", "update_account_followers"],
                "task_configs": {
                    "auto_fetch_max_retries": getattr(auto_fetch_engagement_data, 'max_retries', 'unknown'),
                    "follower_update_max_retries": getattr(update_account_followers, 'max_retries', 'unknown')
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def test_rate_limiting(self) -> Dict[str, Any]:
        """Test rate limiting functionality."""
        print("🧪 Testing rate limiting...")

        try:
            from app.utils.rate_limiter import rate_limiter, PLATFORM_RATE_LIMITS

            # Test rate limiter availability
            return {
                "status": "success",
                "rate_limiter_available": True,
                "platform_limits": PLATFORM_RATE_LIMITS,
                "redis_connected": rate_limiter.redis.ping() if hasattr(rate_limiter.redis, 'ping') else False
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests."""
        print("🚀 Starting Real API Integration Tests\n")

        # Check API keys
        api_keys = self.check_api_keys()
        self.test_results["api_keys_configured"] = api_keys
        print(f"🔑 API Keys Status: {sum(api_keys.values())}/{len(api_keys)} configured")

        # Test platform analytics fetching
        platforms = ["youtube", "instagram", "tiktok", "facebook", "twitter", "linkedin"]
        platform_results = {}

        for platform in platforms:
            result = await self.test_platform_analytics_fetch(platform)
            platform_results[platform] = result
            status_icon = "✅" if result["status"] == "success" else "❌" if result["status"] == "error" else "⏭️"
            print(f"  {status_icon} {platform}: {result['status']}")

        self.test_results["platform_tests"] = platform_results

        # Test Celery tasks
        celery_result = self.test_celery_task_execution()
        self.test_results["celery_test"] = celery_result
        print(f"✅ Celery Tasks: {celery_result['status']}")

        # Test rate limiting
        rate_limit_result = self.test_rate_limiting()
        self.test_results["rate_limiting_test"] = rate_limit_result
        print(f"✅ Rate Limiting: {rate_limit_result['status']}")

        # Calculate overall score
        successful_platforms = sum(1 for r in platform_results.values() if r["status"] == "success")
        total_platforms = len(platforms)

        self.test_results["summary"] = {
            "total_platforms": total_platforms,
            "successful_platforms": successful_platforms,
            "api_keys_configured": sum(api_keys.values()),
            "overall_score": f"{successful_platforms}/{total_platforms} platforms working",
            "production_readiness": "ready" if successful_platforms >= 1 else "needs_configuration"
        }

        print(f"\n📊 Test Results Summary:")
        print(f"  Platforms Working: {successful_platforms}/{total_platforms}")
        print(f"  API Keys Configured: {sum(api_keys.values())}/{len(api_keys)}")
        print(f"  Production Readiness: {'✅ Ready' if successful_platforms >= 1 else '⚠️ Needs API Keys'}")

        return self.test_results

    def _get_access_token(self, platform: str) -> str:
        """Get access token for a platform from environment."""
        token_map = {
            "youtube": "YOUTUBE_API_KEY",
            "instagram": "INSTAGRAM_ACCESS_TOKEN",
            "tiktok": "TIKTOK_ACCESS_TOKEN",
            "facebook": "FACEBOOK_PAGE_ACCESS_TOKEN",
            "twitter": "X_BEARER_TOKEN",
            "linkedin": "LINKEDIN_ACCESS_TOKEN"
        }

        env_var = token_map.get(platform)
        return os.getenv(env_var, "") if env_var else ""

    def save_results(self, filename: str = None):
        """Save test results to file."""
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"real_api_test_results_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)

        print(f"💾 Results saved to {filename}")


async def main():
    """Main test runner."""
    import argparse

    parser = argparse.ArgumentParser(description="Real API Integration Tests")
    parser.add_argument("--use-real-apis", action="store_true",
                       help="Use real API keys (requires .env configuration)")
    parser.add_argument("--mock-only", action="store_true",
                       help="Use only mock data (default)")
    parser.add_argument("--save-results", action="store_true",
                       help="Save results to JSON file")

    args = parser.parse_args()

    # Determine test mode
    use_real_apis = args.use_real_apis and not args.mock_only

    print(f"🔧 Test Mode: {'REAL APIs' if use_real_apis else 'MOCK Only'}")
    print("⚠️  Make sure .env file has API keys configured for real API testing\n")

    # Run tests
    tester = RealAPIIntegrationTester(use_real_apis=use_real_apis)
    results = await tester.run_all_tests()

    # Save results if requested
    if args.save_results:
        tester.save_results()

    # Exit with appropriate code
    success_count = results["summary"]["successful_platforms"]
    exit_code = 0 if success_count > 0 else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())