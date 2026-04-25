"""
Analytics tasks - Performance tracking and data aggregation.
"""

import logging
from datetime import datetime, timedelta
from celery import shared_task
import time
import random

from app.core.database import SessionLocal
from app.models import Post, Analytics, Account, Trend, Hashtag, Log
from sqlalchemy import func

logger = logging.getLogger(__name__)


# ============================================================================
# Fetch Analytics Task
# ============================================================================

@shared_task(bind=True, name='app.tasks.analytics_tasks.fetch_analytics')
def fetch_analytics(self, post_id: int = None, account_id: int = None):
    """
    Fetch analytics from social media platforms.
    
    Can fetch for specific post or entire account.
    
    Args:
        post_id: Specific post ID to fetch analytics for
        account_id: Specific account ID to fetch analytics for
    
    Returns:
        dict: Analytics data collected
    """
    db = SessionLocal()
    
    try:
        self.update_state(state='PROCESSING', meta={'progress': 10})
        
        if post_id:
            posts = db.query(Post).filter(Post.id == post_id).all()
            logger.info(f"Fetching analytics for post {post_id}")
        elif account_id:
            posts = db.query(Post).filter(Post.account_id == account_id).all()
            logger.info(f"Fetching analytics for account {account_id}")
        else:
            raise ValueError("Either post_id or account_id must be provided")
        
        if not posts:
            logger.warning("No posts found for analytics fetch")
            return {"message": "No posts found", "count": 0}
        
        self.update_state(state='PROCESSING', meta={'progress': 30, 'stage': 'calling_platform_apis'})
        
        collected_count = 0
        
        for idx, post in enumerate(posts):
            progress = 30 + int((idx / len(posts)) * 50)
            self.update_state(state='PROCESSING', meta={
                'progress': progress,
                'current_post': post.id,
                'processed': idx,
                'total': len(posts),
            })
            
            try:
                # Simulate platform API calls (replace with actual APIs)
                time.sleep(0.3)
                
                # Mock analytics data
                analytics_data = _get_mock_analytics(post)
                
                # Save analytics to database
                for platform, data in analytics_data.items():
                    analytics = Analytics(
                        user_id=post.user_id,
                        post_id=post.id,
                        account_id=post.account_id,
                        platform=platform,
                        views=data["views"],
                        likes=data["likes"],
                        comments=data["comments"],
                        shares=data["shares"],
                        saves=data["saves"],
                        reach=data["reach"],
                        impressions=data["impressions"],
                        engagement_rate=data["engagement_rate"],
                        click_through_rate=data.get("click_through_rate"),
                        video_completion_rate=data.get("video_completion_rate"),
                        timestamp=datetime.utcnow(),
                    )
                    
                    db.add(analytics)
                    collected_count += 1
                
                db.commit()
                logger.info(f"Analytics fetched for post {post.id}")
                
            except Exception as e:
                logger.error(f"Failed to fetch analytics for post {post.id}: {str(e)}")
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'stage': 'complete',
            'total_collected': collected_count,
        })
        
        logger.info(f"Analytics fetch completed: {collected_count} records")
        
        return {
            "post_ids": [p.id for p in posts],
            "total_records_collected": collected_count,
            "collected_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Analytics fetch failed: {str(e)}", exc_info=True)
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise
        
    finally:
        db.close()


# ============================================================================
# Aggregate Analytics Task
# ============================================================================

@shared_task(bind=True, name='app.tasks.analytics_tasks.aggregate_daily_analytics')
def aggregate_daily_analytics(self):
    """
    Aggregate daily analytics for all active accounts and posts.
    
    This task:
    - Combines hourly data into daily summaries
    - Calculates trends
    - Identifies top performing content
    - Updates account metrics
    
    Returns:
        dict: Aggregation results
    """
    db = SessionLocal()
    
    try:
        self.update_state(state='PROCESSING', meta={'progress': 10})
        
        logger.info("Starting daily analytics aggregation")
        
        # Get yesterday's date
        yesterday = datetime.utcnow().date() - timedelta(days=1)
        
        # Get all posts with analytics from yesterday
        analytics_records = db.query(Analytics).filter(
            func.date(Analytics.timestamp) == yesterday
        ).all()
        
        if not analytics_records:
            logger.info("No analytics records found for aggregation")
            return {"message": "No records to aggregate", "date": yesterday.isoformat()}
        
        self.update_state(state='PROCESSING', meta={'progress': 40, 'stage': 'aggregating'})
        
        # Group by account and calculate totals
        account_totals = {}
        for record in analytics_records:
            if record.account_id not in account_totals:
                account_totals[record.account_id] = {
                    "views": 0,
                    "likes": 0,
                    "comments": 0,
                    "engagement_rate": [],
                    "posts": set(),
                }
            
            totals = account_totals[record.account_id]
            totals["views"] += record.views
            totals["likes"] += record.likes
            totals["comments"] += record.comments
            totals["engagement_rate"].append(record.engagement_rate or 0)
            totals["posts"].add(record.post_id)
        
        self.update_state(state='PROCESSING', meta={'progress': 70, 'stage': 'updating_accounts'})
        
        # Update account metrics
        for account_id, totals in account_totals.items():
            account = db.query(Account).filter(Account.id == account_id).first()
            if account:
                avg_engagement = sum(totals["engagement_rate"]) / len(totals["engagement_rate"])
                account.last_analytics_update = datetime.utcnow()
                account.engagement_rate = avg_engagement
                db.commit()
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'stage': 'complete',
            'accounts_aggregated': len(account_totals),
        })
        
        logger.info(f"Daily aggregation completed for {len(account_totals)} accounts")
        
        return {
            "date": yesterday.isoformat(),
            "accounts_aggregated": len(account_totals),
            "total_records": len(analytics_records),
            "aggregated_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Daily aggregation failed: {str(e)}", exc_info=True)
        raise
        
    finally:
        db.close()


# ============================================================================
# Fetch Trending Topics Task
# ============================================================================

@shared_task(bind=True, name='app.tasks.analytics_tasks.fetch_trending_topics')
def fetch_trending_topics(self):
    """
    Fetch trending topics from multiple sources.
    
    Sources:
    - Google Trends
    - YouTube Trending
    - Reddit Trending (r/all, r/popular)
    - Twitter Trending
    - TikTok Trending
    - Instagram Reels Trending
    
    Returns:
        dict: Trending topics data
    """
    db = SessionLocal()
    
    try:
        self.update_state(state='PROCESSING', meta={'progress': 10})
        
        logger.info("Fetching trending topics")
        
        self.update_state(state='PROCESSING', meta={'progress': 30, 'stage': 'calling_trend_apis'})
        
        # Simulate API calls to various sources
        time.sleep(1)
        
        # Mock trending data
        trending_data = {
            "instagram": [
                {"title": "#FYP", "growth": 12.5, "saturation": "high"},
                {"title": "#Reels", "growth": 8.3, "saturation": "high"},
                {"title": "#Trending", "growth": 5.2, "saturation": "medium"},
            ],
            "tiktok": [
                {"title": "#ForYou", "growth": 15.2, "saturation": "high"},
                {"title": "#FYP", "growth": 12.8, "saturation": "high"},
                {"title": "#Viral", "growth": 9.1, "saturation": "medium"},
            ],
            "youtube": [
                {"title": "Shorts", "growth": 20.5, "saturation": "medium"},
                {"title": "Gaming", "growth": 11.2, "saturation": "high"},
                {"title": "Music", "growth": 8.7, "saturation": "high"},
            ],
        }
        
        self.update_state(state='PROCESSING', meta={'progress': 60, 'stage': 'saving_trends'})
        
        saved_count = 0
        for platform, trends in trending_data.items():
            for trend_data in trends:
                # Check if trend already exists
                existing = db.query(Trend).filter(
                    Trend.title == trend_data["title"],
                    Trend.platform == platform,
                ).first()
                
                if not existing:
                    trend = Trend(
                        title=trend_data["title"],
                        description=f"Trending on {platform}",
                        platform=platform,
                        source=f"{platform}_api",
                        growth_rate=trend_data["growth"],
                        saturation_level=trend_data["saturation"],
                        language="english",
                        region="global",
                        recommendations={
                            "content_types": ["reel", "short", "post"],
                            "best_time": "evening",
                        },
                    )
                    db.add(trend)
                    saved_count += 1
        
        db.commit()
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'trends_found': saved_count,
            'stage': 'complete',
        })
        
        logger.info(f"Trending topics fetch completed: {saved_count} new trends")
        
        return {
            "new_trends": saved_count,
            "platforms_covered": list(trending_data.keys()),
            "fetched_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Trending topics fetch failed: {str(e)}", exc_info=True)
        raise
        
    finally:
        db.close()


# ============================================================================
# Cleanup Old Analytics Task
# ============================================================================

@shared_task(bind=True, name='app.tasks.analytics_tasks.cleanup_old_results')
def cleanup_old_results(self, days: int = 90):
    """
    Clean up old analytics records to save storage.
    
    Keeps detailed records for 90 days, older records are aggregated
    or deleted based on policy.
    
    Args:
        days: Number of days to keep detailed records (default: 90)
    
    Returns:
        dict: Cleanup results
    """
    db = SessionLocal()
    
    try:
        self.update_state(state='PROCESSING', meta={'progress': 10})
        
        logger.info(f"Cleaning up analytics older than {days} days")
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Delete old analytics records
        old_records = db.query(Analytics).filter(
            Analytics.timestamp < cutoff_date
        ).count()
        
        self.update_state(state='PROCESSING', meta={'progress': 50, 'stage': 'deleting_old_records'})
        
        db.query(Analytics).filter(
            Analytics.timestamp < cutoff_date
        ).delete()
        
        db.commit()
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'deleted_records': old_records,
        })
        
        logger.info(f"Cleanup completed: Deleted {old_records} old records")
        
        return {
            "deleted_records": old_records,
            "cutoff_date": cutoff_date.isoformat(),
            "cleanup_date": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}", exc_info=True)
        raise
        
    finally:
        db.close()


# ============================================================================
# Calculate Insights Task
# ============================================================================

@shared_task(bind=True, name='app.tasks.analytics_tasks.calculate_insights')
def calculate_insights(self, account_id: int, period: str = "week"):
    """
    Calculate AI-powered insights from analytics data.
    
    Analyzes:
    - Engagement trends
    - Growth patterns
    - Audience demographics
    - Best performing content
    - Recommendations
    
    Args:
        account_id: Account ID to analyze
        period: Analysis period (week, month, quarter, year)
    
    Returns:
        dict: Generated insights and recommendations
    """
    db = SessionLocal()
    
    try:
        self.update_state(state='PROCESSING', meta={'progress': 20})
        
        logger.info(f"Calculating insights for account {account_id}")
        
        # Get date range based on period
        today = datetime.utcnow()
        if period == "week":
            start_date = today - timedelta(days=7)
        elif period == "month":
            start_date = today - timedelta(days=30)
        elif period == "quarter":
            start_date = today - timedelta(days=90)
        else:  # year
            start_date = today - timedelta(days=365)
        
        self.update_state(state='PROCESSING', meta={'progress': 50, 'stage': 'analyzing_data'})
        
        # Fetch analytics for period
        analytics = db.query(Analytics).filter(
            Analytics.account_id == account_id,
            Analytics.timestamp >= start_date,
        ).all()
        
        if not analytics:
            logger.warning(f"No analytics found for account {account_id}")
            return {"message": "No analytics data available", "account_id": account_id}
        
        # Calculate metrics
        total_views = sum(a.views for a in analytics)
        avg_engagement = sum(a.engagement_rate for a in analytics) / len(analytics)
        
        # Generate recommendations based on analysis
        recommendations = []
        if avg_engagement < 3:
            recommendations.append("Increase posting frequency")
            recommendations.append("Improve content hooks")
        if avg_engagement > 8:
            recommendations.append("Monetization opportunity - consider partnerships")
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'insights_generated': True,
        })
        
        logger.info(f"Insights calculated for account {account_id}")
        
        return {
            "account_id": account_id,
            "period": period,
            "total_views": total_views,
            "average_engagement_rate": round(avg_engagement, 2),
            "recommendations": recommendations,
            "calculated_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Insight calculation failed: {str(e)}", exc_info=True)
        raise
        
    finally:
        db.close()


# ============================================================================
# Helper Functions
# ============================================================================

def _get_mock_analytics(post: Post) -> dict:
    """
    Generate mock analytics data for a post.
    
    Args:
        post: Post object
    
    Returns:
        dict: Analytics data by platform
    """
    platforms = post.published_platforms or ["instagram"]
    analytics = {}
    
    for platform in platforms:
        views = random.randint(100, 50000)
        likes = int(views * random.uniform(0.01, 0.15))
        comments = int(likes * random.uniform(0.05, 0.3))
        engagement = ((likes + comments) / views * 100) if views > 0 else 0
        
        analytics[platform] = {
            "views": views,
            "likes": likes,
            "comments": comments,
            "shares": random.randint(0, int(likes * 0.2)),
            "saves": random.randint(0, int(likes * 0.5)),
            "reach": int(views * random.uniform(0.8, 1.0)),
            "impressions": int(views * random.uniform(1.0, 1.5)),
            "engagement_rate": round(engagement, 2),
            "click_through_rate": round(random.uniform(0.5, 5.0), 2),
            "video_completion_rate": round(random.uniform(20, 95), 1) if post.content_type in ["reel", "short", "video"] else None,
        }
    
    return analytics
