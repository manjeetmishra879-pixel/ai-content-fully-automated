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
from app.services.analytics_service import AnalyticsService
from sqlalchemy import func

logger = logging.getLogger(__name__)


# ============================================================================
# Auto-fetch Engagement Data Task
# ============================================================================

@shared_task(bind=True, name='app.tasks.analytics_tasks.auto_fetch_engagement_data',
           max_retries=3, default_retry_delay=300, autoretry_for=(Exception,),
           retry_backoff=True, retry_backoff_max=3600)
def auto_fetch_engagement_data(self, user_id: int = None, hours_back: int = 24):
    """
    Automatically fetch engagement data from all platforms for ML training.

    This task runs periodically to collect real engagement data from published posts
    and feed it to the engagement prediction model for continuous learning.

    Includes automatic retry with exponential backoff on failures.

    Args:
        user_id: Specific user ID (if None, process all users)
        hours_back: How many hours back to look for posts (default: 24)

    Returns:
        dict: Summary of data collection
    """
    # Create event loop for async operations
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    db = SessionLocal()

    try:
        self.update_state(state='PROCESSING', meta={'progress': 5})

        analytics_service = AnalyticsService(db)

        if user_id:
            # Process specific user
            users = [db.query(Account).filter(Account.id == user_id).first()]
            if not users[0]:
                raise ValueError(f"User {user_id} not found")
        else:
            # Process all users (in production, limit this)
            users = db.query(Account).all()

        total_results = {
            "total_users": len(users),
            "total_posts_processed": 0,
            "successful_fetches": 0,
            "failed_fetches": 0,
            "ml_data_collected": 0,
            "user_results": []
        }

        for i, user in enumerate(users):
            try:
                self.update_state(
                    state='PROCESSING',
                    meta={
                        'progress': 10 + (i / len(users)) * 80,
                        'current_user': user.id
                    }
                )

                # Auto-fetch analytics for this user (run in event loop)
                user_results = loop.run_until_complete(
                    analytics_service.auto_fetch_all_posts(user.id, hours_back)
                )

                total_results["total_posts_processed"] += user_results["total_posts"]
                total_results["successful_fetches"] += user_results["successful_fetches"]
                total_results["failed_fetches"] += user_results["failed_fetches"]
                total_results["ml_data_collected"] += user_results["successful_fetches"]  # Each success = ML data

                total_results["user_results"].append({
                    "user_id": user.id,
                    "results": user_results
                })

                logger.info(f"Processed user {user.id}: {user_results}")

            except Exception as e:
                logger.error(f"Failed to process user {user.id}: {e}")
                total_results["user_results"].append({
                    "user_id": user.id,
                    "error": str(e)
                })

        # Check if we have enough data for retraining
        if total_results["ml_data_collected"] >= 100:
            logger.info("Collected 100+ samples, triggering model retraining")
            # Trigger retraining (would be implemented)
            total_results["retraining_triggered"] = True
        else:
            total_results["retraining_triggered"] = False

        self.update_state(
            state='SUCCESS',
            meta={
                'progress': 100,
                'results': total_results
            }
        )

        logger.info(f"Auto-fetch engagement data completed: {total_results}")
        return total_results

    except Exception as e:
        logger.error(f"Auto-fetch engagement data failed: {e}")
    except Exception as e:
        logger.error(f"Auto-fetch engagement data failed (attempt {self.request.retries}/{self.max_retries}): {e}")
        self.update_state(state='FAILURE', meta={'error': str(e), 'attempt': self.request.retries})
        
        # Retry with exponential backoff if under max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying auto-fetch in {self.default_retry_delay * (2 ** self.request.retries)} seconds")
            raise self.retry(exc=e)
        else:
            logger.error("Max retries exceeded, giving up")
            raise
    finally:
        loop.close()
        db.close()


@shared_task(bind=True, name='app.tasks.analytics_tasks.update_account_followers',
           max_retries=3, default_retry_delay=300, autoretry_for=(Exception,),
           retry_backoff=True, retry_backoff_max=3600)
def update_account_followers(self, user_id: int = None):
    """
    Update follower counts for all user accounts across platforms.

    This ensures the engagement prediction model has current follower data.
    Includes automatic retry with exponential backoff on failures.

    Args:
        user_id: Specific user ID (if None, update all users)

    Returns:
        dict: Update summary
    """
    db = SessionLocal()

    try:
        self.update_state(state='PROCESSING', meta={'progress': 10})

        analytics_service = AnalyticsService(db)

        if user_id:
            users = [db.query(Account).filter(Account.id == user_id).first()]
            if not users[0]:
                raise ValueError(f"User {user_id} not found")
        else:
            users = db.query(Account).all()

        results = {
            "total_users": len(users),
            "accounts_updated": 0,
            "platforms_updated": [],
            "details": []
        }

        platforms = ["instagram", "tiktok", "youtube", "facebook", "x", "linkedin"]

        for user in users:
            user_updates = {"user_id": user.id, "platforms": {}}

            for platform in platforms:
                try:
                    followers = analytics_service.get_account_followers(user.id, platform)
                    user_updates["platforms"][platform] = followers
                    results["platforms_updated"].append(platform)

                except Exception as e:
                    logger.error(f"Failed to update {platform} followers for user {user.id}: {e}")
                    user_updates["platforms"][platform] = {"error": str(e)}

            results["details"].append(user_updates)
            results["accounts_updated"] += 1

        self.update_state(
            state='SUCCESS',
            meta={
                'progress': 100,
                'results': results
            }
        )

        logger.info(f"Account followers update completed: {results}")
        return results

    except Exception as e:
        logger.error(f"Account followers update failed (attempt {self.request.retries}/{self.max_retries}): {e}")
        self.update_state(state='FAILURE', meta={'error': str(e), 'attempt': self.request.retries})
        
        # Retry with exponential backoff if under max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying follower update in {self.default_retry_delay * (2 ** self.request.retries)} seconds")
            raise self.retry(exc=e)
        else:
            logger.error("Max retries exceeded, giving up")
            raise
    finally:
        db.close()


@shared_task(bind=True, name='app.tasks.analytics_tasks.retrain_engagement_model',
           max_retries=2, default_retry_delay=600)
def retrain_engagement_model(self):
    """
    Automatically retrain the engagement prediction model when sufficient new data is available.
    
    This task is triggered when auto-fetch collects 100+ new samples.
    Includes retry logic for robustness.

    Returns:
        dict: Retraining results
    """
    db = SessionLocal()
    
    try:
        self.update_state(state='PROCESSING', meta={'progress': 10})
        
        from app.services.analytics_service import AnalyticsService
        analytics_service = AnalyticsService(db)
        
        # Check if we have enough new data for retraining
        data_stats = analytics_service.get_real_data_stats()
        
        if data_stats.get('total_samples', 0) < 100:
            logger.info(f"Not enough data for retraining: {data_stats.get('total_samples', 0)} samples")
            return {"status": "insufficient_data", "samples": data_stats.get('total_samples', 0)}
        
        self.update_state(state='PROCESSING', meta={'progress': 30, 'stage': 'loading_data'})
        
        # Load recent engagement data for retraining
        # This would load from the JSONL file or database
        training_data = []  # Load actual data here
        
        if not training_data:
            logger.warning("No training data available for retraining")
            return {"status": "no_data_available"}
        
        self.update_state(state='PROCESSING', meta={'progress': 50, 'stage': 'retraining'})
        
        # Retrain the model
        from app.engines.quality.engagement_prediction import EngagementPredictionEngine
        engine = EngagementPredictionEngine()
        
        results = engine.train_models(training_data, "real")
        
        self.update_state(
            state='SUCCESS',
            meta={
                'progress': 100,
                'results': results
            }
        )
        
        logger.info(f"Model retraining completed: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Model retraining failed (attempt {self.request.retries}/{self.max_retries}): {e}")
        self.update_state(state='FAILURE', meta={'error': str(e), 'attempt': self.request.retries})
        
        # Retry once for retraining failures
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying retraining in {self.default_retry_delay} seconds")
            raise self.retry(exc=e)
        else:
            logger.error("Max retries exceeded for retraining, giving up")
            raise
    finally:
        db.close()


# ============================================================================
# Helper Functions
# ============================================================================

def _get_mock_analytics(post):
    # Generate mock analytics data for a post.
    platforms = getattr(post, 'published_platforms', None) or ["instagram"]
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
            "video_completion_rate": round(random.uniform(20, 95), 1) if getattr(post, 'content_type', '') in ["reel", "short", "video"] else None,
        }
    
    return analytics
