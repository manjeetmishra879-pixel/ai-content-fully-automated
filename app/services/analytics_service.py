"""
Analytics tracking and reporting service with auto-fetch integration
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.models import Post, Analytics, Trend, User
from app.engines import get_engine
from app.core.config import settings
from app.utils.rate_limiter import rate_limit, exponential_backoff, RateLimitExceededError

# Platform API endpoints
PLATFORM_APIS = {
    "instagram": "https://graph.instagram.com",
    "tiktok": "https://open-api.tiktok.com",
    "youtube": "https://www.googleapis.com/youtube/v3",
    "facebook": "https://graph.facebook.com",
    "x": "https://api.twitter.com/2",
    "linkedin": "https://api.linkedin.com/v2"
}

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for analytics operations with auto-fetch"""

    def __init__(self, db: Session, redis_client=None):
        self.db = db
        self.redis = redis_client
        self.analytics_engine = get_engine("analytics")
        self.best_time_engine = get_engine("best_time")
        self.engagement_engine = get_engine("engagement_prediction")

    async def track_performance(self, post_id: int, platform: str,
                              metrics: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Track content performance on platform"""
        post = self.db.query(Post).filter(
            Post.id == post_id,
            Post.user_id == user_id
        ).first()

        if not post:
            raise ValueError(f"Post {post_id} not found")

        # Create analytics record
        analytics = Analytics(
            post_id=post_id,
            platform=platform,
            impressions=metrics.get("impressions", 0),
            likes=metrics.get("likes", 0),
            comments=metrics.get("comments", 0),
            shares=metrics.get("shares", 0),
            saves=metrics.get("saves", 0),
            clicks=metrics.get("clicks", 0),
            reach=metrics.get("reach", 0),
            engagement_rate=metrics.get("engagement_rate", 0.0),
            extra_metrics=metrics
        )

        self.db.add(analytics)
        self.db.commit()
        self.db.refresh(analytics)

        # Auto-collect for ML training
        await self._collect_for_ml_training(post_id, platform, metrics, user_id)

        return {
            "analytics_id": analytics.id,
            "tracked": True,
            "ml_collected": True
        }

    async def _collect_for_ml_training(self, post_id: int, platform: str,
                                     metrics: Dict[str, Any], user_id: int) -> None:
        """Automatically collect engagement data for ML model training"""

        try:
            # Calculate derived metrics
            total_engagement = (
                metrics.get("likes", 0) +
                metrics.get("comments", 0) +
                metrics.get("shares", 0) +
                metrics.get("saves", 0)
            )

            impressions = metrics.get("impressions", 1)  # Avoid division by zero
            completion_rate = metrics.get("completion_rate", 0.0)
            watch_time = metrics.get("watch_time_seconds", 0.0)
            duration = metrics.get("duration_seconds", 30.0)

            # Calculate rates
            like_rate = metrics.get("likes", 0) / impressions if impressions > 0 else 0
            share_rate = metrics.get("shares", 0) / impressions if impressions > 0 else 0
            comment_rate = metrics.get("comments", 0) / impressions if impressions > 0 else 0

            # Skip rates (where available)
            skip_3s = metrics.get("skip_rate_3s")
            skip_10s = metrics.get("skip_rate_10s")
            skip_30s = metrics.get("skip_rate_30s")

            # Prepare data for ML collection
            ml_data = {
                "completion_rate": completion_rate,
                "like_rate": like_rate,
                "share_rate": share_rate,
                "platform": platform,
                "impressions": impressions,
                "total_engagement": total_engagement,
                "engagement_rate": total_engagement / impressions if impressions > 0 else 0,
                "watch_time_seconds": watch_time,
                "duration_seconds": duration
            }

            # Add skip rates if available
            if skip_3s is not None:
                ml_data["skip_3s"] = skip_3s
            if skip_10s is not None:
                ml_data["skip_10s"] = skip_10s
            if skip_30s is not None:
                ml_data["skip_30s"] = skip_30s

            # Collect for ML training
            result = self.engagement_engine.collect_real_engagement_data(post_id, ml_data)

            logger.info(f"Collected ML data for post {post_id}: {result}")

        except Exception as e:
            logger.error(f"Failed to collect ML data for post {post_id}: {e}")

    async def fetch_platform_analytics(self, platform: str, post_id: str,
                                     access_token: str, user_id: int = None) -> Dict[str, Any]:
        """Fetch analytics from platform APIs with rate limiting"""

        try:
            if platform == "instagram":
                return await self._fetch_instagram_analytics(post_id, access_token, user_id)
            elif platform == "tiktok":
                return await self._fetch_tiktok_analytics(post_id, access_token, user_id)
            elif platform == "youtube":
                return await self._fetch_youtube_analytics(post_id, access_token, user_id)
            elif platform == "facebook":
                return await self._fetch_facebook_analytics(post_id, access_token, user_id)
            elif platform == "x":
                return await self._fetch_twitter_analytics(post_id, access_token, user_id)
            elif platform == "linkedin":
                return await self._fetch_linkedin_analytics(post_id, access_token, user_id)
            else:
                raise ValueError(f"Unsupported platform: {platform}")

        except RateLimitExceededError:
            logger.warning(f"Rate limit exceeded for {platform} API")
            return {}  # Return empty data, will fall back to mock
        except Exception as e:
            logger.error(f"Failed to fetch {platform} analytics for post {post_id}: {e}")
            return {}

    @rate_limit(max_calls=200, period_seconds=3600, platform="instagram")
    async def _fetch_instagram_analytics(self, post_id: str, access_token: str, user_id: int = None) -> Dict[str, Any]:
        """Fetch Instagram analytics (limited data available)"""
        # Note: Instagram Basic Display API has limited metrics
        # In production, use Instagram Graph API with business account

        # Mock response - in production, make real API call
        return {
            "impressions": 12500,
            "likes": 450,
            "comments": 23,
            "shares": 12,
            "saves": 89,
            "reach": 9800,
            "engagement_rate": 0.046,
            # Skip rates not available for Instagram
            "completion_rate": 0.68,
            "watch_time_seconds": 20.4,
            "duration_seconds": 30.0
        }

    @rate_limit(max_calls=100, period_seconds=3600, platform="tiktok")
    async def _fetch_tiktok_analytics(self, post_id: str, access_token: str, user_id: int = None) -> Dict[str, Any]:
        """Fetch TikTok analytics"""
        # Mock response - in production, use TikTok Marketing API

        return {
            "impressions": 25000,
            "likes": 1200,
            "comments": 45,
            "shares": 89,
            "saves": 234,
            "reach": 18500,
            "engagement_rate": 0.063,
            # Skip rates not available for TikTok
            "completion_rate": 0.72,
            "watch_time_seconds": 21.6,
            "duration_seconds": 30.0
        }

    @rate_limit(max_calls=10000, period_seconds=86400, platform="youtube")
    async def _fetch_youtube_analytics(self, post_id: str, access_token: str, user_id: int = None) -> Dict[str, Any]:
        """Fetch YouTube analytics (full detailed data available)"""
        # Mock response - in production, use YouTube Analytics API

        return {
            "impressions": 50000,
            "likes": 2100,
            "comments": 156,
            "shares": 234,
            "saves": 0,  # YouTube doesn't have saves
            "reach": 35000,
            "engagement_rate": 0.051,
            # Detailed watch time analytics available
            "completion_rate": 0.65,
            "watch_time_seconds": 19.5,
            "duration_seconds": 30.0,
            # Skip rates available for YouTube
            "skip_rate_3s": 0.12,
            "skip_rate_10s": 0.28,
            "skip_rate_30s": 0.45,
            "average_view_duration": 19.5
        }

    async def _fetch_facebook_analytics(self, post_id: str, access_token: str) -> Dict[str, Any]:
        """Fetch Facebook analytics"""
        # Mock response - limited metrics available

        return {
            "impressions": 8000,
            "likes": 120,
            "comments": 8,
            "shares": 15,
            "reach": 6500,
            "engagement_rate": 0.021,
            # Limited video metrics
            "completion_rate": 0.45,
            "watch_time_seconds": 13.5,
            "duration_seconds": 30.0
        }

    async def _fetch_twitter_analytics(self, post_id: str, access_token: str) -> Dict[str, Any]:
        """Fetch Twitter/X analytics"""
        # Mock response - basic metrics only

        return {
            "impressions": 15000,
            "likes": 320,
            "comments": 12,
            "shares": 45,  # Retweets
            "reach": 12000,
            "engagement_rate": 0.026,
            # No video completion metrics
        }

    async def _fetch_linkedin_analytics(self, post_id: str, access_token: str) -> Dict[str, Any]:
        """Fetch LinkedIn analytics"""
        # Mock response - professional content metrics

        return {
            "impressions": 5200,
            "likes": 89,
            "comments": 34,
            "shares": 12,
            "reach": 4100,
            "engagement_rate": 0.026,
            # Limited video metrics
            "completion_rate": 0.58,
            "watch_time_seconds": 17.4,
            "duration_seconds": 30.0
        }

    async def auto_fetch_all_posts(self, user_id: int, hours_back: int = 24) -> Dict[str, Any]:
        """Auto-fetch analytics for all published posts in the last N hours"""

        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

        # Get posts that need analytics fetch
        posts = self.db.query(Post).filter(
            Post.user_id == user_id,
            Post.created_at >= cutoff_time,
            Post.status == "published"
        ).all()

        results = {
            "total_posts": len(posts),
            "successful_fetches": 0,
            "failed_fetches": 0,
            "details": []
        }

        for post in posts:
            try:
                # Get user's platform tokens (mock - in production, get from database)
                platform_tokens = self._get_user_platform_tokens(user_id)

                if post.platform in platform_tokens:
                    # Fetch analytics
                    metrics = await self.fetch_platform_analytics(
                        post.platform,
                        post.platform_post_id or str(post.id),
                        platform_tokens[post.platform]
                    )

                    if metrics:
                        # Track performance
                        await self.track_performance(
                            post.id, post.platform, metrics, user_id
                        )

                        results["successful_fetches"] += 1
                        results["details"].append({
                            "post_id": post.id,
                            "platform": post.platform,
                            "status": "success",
                            "metrics_collected": len(metrics)
                        })
                    else:
                        results["failed_fetches"] += 1
                        results["details"].append({
                            "post_id": post.id,
                            "platform": post.platform,
                            "status": "no_data"
                        })

            except Exception as e:
                logger.error(f"Failed to fetch analytics for post {post.id}: {e}")
                results["failed_fetches"] += 1
                results["details"].append({
                    "post_id": post.id,
                    "platform": post.platform,
                    "status": "error",
                    "error": str(e)
                })

        return results

    def _get_user_platform_tokens(self, user_id: int) -> Dict[str, str]:
        """Get user's platform access tokens (mock implementation)"""
        # In production, fetch from database
        # For now, return mock tokens
        return {
            "instagram": "mock_instagram_token",
            "tiktok": "mock_tiktok_token",
            "youtube": "mock_youtube_token",
            "facebook": "mock_facebook_token",
            "x": "mock_twitter_token",
            "linkedin": "mock_linkedin_token"
        }

    def get_competitor_engagement(self, platform: str, content_type: str,
                                trend_keywords: List[str]) -> float:
        """Get average engagement from competitors (mock implementation)"""

        # In production, this would:
        # 1. Search for similar content on platform
        # 2. Fetch their engagement metrics
        # 3. Calculate average

        # Mock competitor engagement based on platform and trends
        base_engagement = {
            "instagram": 0.045,
            "tiktok": 0.065,
            "youtube": 0.035,
            "facebook": 0.025,
            "x": 0.020,
            "linkedin": 0.030
        }

        competitor_avg = base_engagement.get(platform, 0.03)

        # Boost if trending topics
        if trend_keywords:
            competitor_avg *= (1.0 + len(trend_keywords) * 0.1)

        return competitor_avg

    def get_seasonal_trend_factor(self, platform: str, current_date: datetime = None) -> float:
        """Calculate seasonal trend factor"""

        if current_date is None:
            current_date = datetime.utcnow()

        # Seasonal factors based on month and day of week
        month = current_date.month
        day_of_week = current_date.weekday()

        # Holiday seasons boost engagement
        holiday_boost = 1.0
        if month == 12:  # Christmas/New Year
            holiday_boost = 1.3
        elif month in [11, 1]:  # Thanksgiving, Valentine's
            holiday_boost = 1.1
        elif month in [6, 7, 8]:  # Summer
            holiday_boost = 1.05

        # Weekend boost
        weekend_boost = 1.1 if day_of_week >= 5 else 1.0

        # Platform-specific seasonal patterns
        platform_factors = {
            "instagram": 1.0,  # Consistent
            "tiktok": 1.2 if day_of_week in [4, 5, 6] else 0.9,  # Weekend heavy
            "youtube": 1.0,  # Steady
            "facebook": 0.9 if day_of_week in [0, 6] else 1.0,  # Weekday heavy
            "x": 1.1 if day_of_week in [1, 2, 3] else 0.95,  # Business day heavy
            "linkedin": 1.2 if day_of_week in [0, 1, 2, 3, 4] else 0.8  # Work week heavy
        }

        platform_factor = platform_factors.get(platform, 1.0)

        seasonal_factor = holiday_boost * weekend_boost * platform_factor

        return min(seasonal_factor, 2.0)  # Cap at 2x boost

    def get_account_followers(self, user_id: int, platform: str) -> int:
        """Get current follower count for user's account on platform"""

        # In production, this would fetch from platform APIs
        # For now, return mock data based on user_id hash

        # Mock follower counts
        base_followers = {
            "instagram": 15000,
            "tiktok": 25000,
            "youtube": 8500,
            "facebook": 12000,
            "x": 5200,
            "linkedin": 3400
        }

        followers = base_followers.get(platform, 1000)

        # Add some variation based on user_id
        followers = int(followers * (0.8 + (user_id % 10) * 0.04))

        return followers

    async def get_real_vs_synthetic_performance_report(self) -> Dict[str, Any]:
        """Generate report comparing synthetic vs real data performance"""

        # Get model info
        model_info = self.engagement_engine.get_model_info()

        # Get real data stats
        real_data_stats = self.engagement_engine.get_real_data_stats()

        # Calculate performance metrics
        synthetic_performance = model_info.get("model_versions", {}).get("performance", {})

        # Mock real data performance (in production, calculate from actual predictions)
        real_performance = {}
        if real_data_stats["total_samples"] > 0:
            # Simulate real performance (would be calculated from actual data)
            real_performance = {
                "completion_rate": {"mae": 0.08, "r2_score": 0.72},
                "like_rate": {"mae": 0.015, "r2_score": 0.68},
                "share_rate": {"mae": 0.005, "r2_score": 0.65}
            }

        return {
            "data_source": model_info.get("data_source", "unknown"),
            "total_real_samples": real_data_stats["total_samples"],
            "synthetic_performance": synthetic_performance,
            "real_performance": real_performance,
            "performance_gap": self._calculate_performance_gap(synthetic_performance, real_performance),
            "recommendations": self._get_performance_recommendations(real_data_stats)
        }

    def _calculate_performance_gap(self, synthetic: Dict, real: Dict) -> Dict[str, float]:
        """Calculate performance gap between synthetic and real data"""

        gaps = {}
        for metric in ["completion_rate", "like_rate", "share_rate"]:
            if metric in synthetic and metric in real:
                synthetic_r2 = synthetic[metric].get("r2_score", 0)
                real_r2 = real[metric].get("r2_score", 0)
                gaps[f"{metric}_r2_gap"] = synthetic_r2 - real_r2

                synthetic_mae = synthetic[metric].get("mae", 0)
                real_mae = real[metric].get("mae", 0)
                gaps[f"{metric}_mae_gap"] = real_mae - synthetic_mae  # Positive = real is worse

        return gaps

    def _get_performance_recommendations(self, real_data_stats: Dict) -> List[str]:
        """Get recommendations based on real data collection status"""

        recommendations = []

        if real_data_stats["total_samples"] < 50:
            recommendations.append("Collect at least 50 real engagement samples for reliable retraining")

        if real_data_stats["total_samples"] >= 100:
            recommendations.append("Ready for model retraining with real data")

        platforms = real_data_stats.get("platforms", [])
        if len(platforms) < 3:
            recommendations.append("Collect data from more platforms for better generalization")

        return recommendations

        # Update best time learning
        published_at = post.published_at or post.created_at
        engagement = self._calculate_engagement_score(metrics)

        self.best_time_engine.run(
            action="ingest",
            records=[{
                "platform": platform,
                "published_at": published_at.isoformat(),
                "engagement": engagement
            }]
        )

        return {
            "analytics_id": analytics.id,
            "engagement_score": engagement,
            "tracked_at": analytics.created_at.isoformat()
        }

    async def get_dashboard_metrics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get overall dashboard metrics"""
        since_date = datetime.utcnow() - timedelta(days=days)

        # Aggregate metrics
        result = self.db.query(
            Analytics.platform,
            Analytics.impressions,
            Analytics.likes,
            Analytics.comments,
            Analytics.shares,
            Analytics.saves,
            Analytics.engagement_rate
        ).join(Post).filter(
            Post.user_id == user_id,
            Analytics.created_at >= since_date
        ).all()

        total_impressions = sum(r.impressions or 0 for r in result)
        total_likes = sum(r.likes or 0 for r in result)
        total_comments = sum(r.comments or 0 for r in result)
        total_shares = sum(r.shares or 0 for r in result)
        total_saves = sum(r.saves or 0 for r in result)
        avg_engagement = sum(r.engagement_rate or 0 for r in result) / len(result) if result else 0

        # Platform breakdown
        platform_stats = {}
        for r in result:
            platform = r.platform
            if platform not in platform_stats:
                platform_stats[platform] = {
                    "impressions": 0, "likes": 0, "comments": 0,
                    "shares": 0, "saves": 0, "posts": 0
                }
            platform_stats[platform]["impressions"] += r.impressions or 0
            platform_stats[platform]["likes"] += r.likes or 0
            platform_stats[platform]["comments"] += r.comments or 0
            platform_stats[platform]["shares"] += r.shares or 0
            platform_stats[platform]["saves"] += r.saves or 0
            platform_stats[platform]["posts"] += 1

        # Best performing content
        top_posts = self.db.query(
            Post.id, Post.title, Analytics.likes, Analytics.comments, Analytics.shares
        ).join(Analytics).filter(
            Post.user_id == user_id,
            Analytics.created_at >= since_date
        ).order_by((Analytics.likes + Analytics.comments + Analytics.shares).desc()).limit(5).all()

        return {
            "period_days": days,
            "total_impressions": total_impressions,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "total_saves": total_saves,
            "average_engagement_rate": round(avg_engagement, 4),
            "platform_breakdown": platform_stats,
            "top_performing_posts": [
                {
                    "id": p.id,
                    "title": p.title,
                    "total_engagement": (p.likes or 0) + (p.comments or 0) + (p.shares or 0)
                } for p in top_posts
            ]
        }

    async def get_content_analytics(self, content_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get analytics for specific content"""
        content = self.db.query(Post).filter(
            Post.id == content_id,
            Post.user_id == user_id
        ).first()

        if not content:
            return None

        analytics = self.db.query(Analytics).filter(Analytics.post_id == content_id).all()

        if not analytics:
            return {
                "content_id": content_id,
                "title": content.title,
                "analytics": [],
                "summary": {"total_impressions": 0, "total_engagement": 0}
            }

        # Aggregate by platform
        platform_data = {}
        total_impressions = 0
        total_engagement = 0

        for a in analytics:
            platform = a.platform
            if platform not in platform_data:
                platform_data[platform] = {
                    "impressions": 0, "likes": 0, "comments": 0, "shares": 0, "saves": 0,
                    "engagement_rate": 0.0, "data_points": 0
                }

            platform_data[platform]["impressions"] += a.impressions or 0
            platform_data[platform]["likes"] += a.likes or 0
            platform_data[platform]["comments"] += a.comments or 0
            platform_data[platform]["shares"] += a.shares or 0
            platform_data[platform]["saves"] += a.saves or 0
            platform_data[platform]["engagement_rate"] = max(
                platform_data[platform]["engagement_rate"], a.engagement_rate or 0.0
            )
            platform_data[platform]["data_points"] += 1

            total_impressions += a.impressions or 0
            total_engagement += (a.likes or 0) + (a.comments or 0) + (a.shares or 0) + (a.saves or 0)

        return {
            "content_id": content_id,
            "title": content.title,
            "platforms": content.platforms,
            "published_at": content.published_at.isoformat() if content.published_at else None,
            "analytics": platform_data,
            "summary": {
                "total_impressions": total_impressions,
                "total_engagement": total_engagement,
                "platforms_count": len(platform_data)
            }
        }

    async def compare_accounts(self, user_id: int, account_ids: List[int]) -> Dict[str, Any]:
        """Compare performance across accounts"""
        # This would use the analytics engine for comparison
        return self.analytics_engine.run(
            action="compare",
            db=self.db,
            user_id=user_id,
            account_ids=account_ids
        )

    async def get_trending_hashtags(self, user_id: int, platform: str = "instagram") -> List[str]:
        """Get trending hashtags for a platform"""
        return self.analytics_engine.run(
            action="trending_hashtags",
            platform=platform
        )

    async def learn_best_times(self, user_id: int) -> Dict[str, Any]:
        """Learn optimal publishing times"""
        # Get all user's analytics data for learning
        analytics_data = self.db.query(Analytics, Post.published_at).join(Post).filter(
            Post.user_id == user_id,
            Post.published_at.isnot(None)
        ).all()

        records = []
        for analytics, published_at in analytics_data:
            engagement = self._calculate_engagement_score({
                "likes": analytics.likes,
                "comments": analytics.comments,
                "shares": analytics.shares,
                "saves": analytics.saves,
                "impressions": analytics.impressions
            })
            records.append({
                "platform": analytics.platform,
                "published_at": published_at.isoformat(),
                "engagement": engagement
            })

        self.best_time_engine.run(action="ingest", records=records)

        # Return current best times
        return self.best_time_engine.run(action="best_times", platform="all")

    def _calculate_engagement_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate engagement score from metrics"""
        likes = metrics.get("likes", 0) or 0
        comments = metrics.get("comments", 0) or 0
        shares = metrics.get("shares", 0) or 0
        saves = metrics.get("saves", 0) or 0
        impressions = metrics.get("impressions", 0) or 1  # Avoid division by zero

        # Weighted engagement score
        return (likes * 1.0 + comments * 2.0 + shares * 3.0 + saves * 1.5) / impressions
