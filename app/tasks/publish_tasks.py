"""
Content publishing tasks - Multi-platform post publishing.
"""

import logging
from datetime import datetime, timedelta
from celery import shared_task
import time
import random

from app.core.database import SessionLocal
from app.models import Post, Schedule, Account, Log
import pytz

logger = logging.getLogger(__name__)


# ============================================================================
# Post Publishing Task
# ============================================================================

@shared_task(bind=True, name='app.tasks.publish_tasks.publish_post')
def publish_post(self, post_id: int, platforms: list, notify: bool = False):
    """
    Publish post to multiple social media platforms.
    
    Supports:
    - Instagram (feed, reels, stories)
    - TikTok
    - YouTube (Shorts, Videos)
    - Facebook
    - X (Twitter)
    - LinkedIn
    - Pinterest
    - Telegram
    
    Args:
        post_id: Post ID to publish
        platforms: List of platforms to publish to
        notify: Notify followers after publishing
    
    Returns:
        dict: Publication results per platform
    """
    db = SessionLocal()
    
    try:
        self.update_state(state='PROCESSING', meta={'progress': 10})
        
        # Verify post exists
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise ValueError(f"Post {post_id} not found")
        
        logger.info(f"Publishing post {post_id} to platforms: {platforms}")
        
        # Verify user has accounts for all target platforms
        user_accounts = db.query(Account).filter(
            Account.user_id == post.user_id,
            Account.platform.in_(platforms)
        ).all()
        
        available_platforms = {acc.platform for acc in user_accounts}
        unavailable_platforms = set(platforms) - available_platforms
        
        if unavailable_platforms:
            logger.warning(f"No accounts found for platforms: {unavailable_platforms}")
        
        platforms_status = {}
        published_urls = {}
        total_platforms = len([p for p in platforms if p in available_platforms])
        
        for idx, platform in enumerate(platforms):
            progress = int((idx / max(total_platforms, 1)) * 90)
            self.update_state(state='PROCESSING', meta={
                'progress': progress,
                'current_platform': platform,
            })
            
            try:
                if platform not in available_platforms:
                    platforms_status[platform] = "no_account"
                    continue
                
                account = next(acc for acc in user_accounts if acc.platform == platform)
                
                # Simulate platform API call
                time.sleep(0.5)
                
                # Mock publication
                url = _publish_to_platform(post, account, platform)
                
                platforms_status[platform] = "published"
                published_urls[platform] = url
                
                logger.info(f"Published to {platform}: {url}")
                
            except Exception as e:
                logger.error(f"Failed to publish to {platform}: {str(e)}")
                platforms_status[platform] = f"failed: {str(e)}"
        
        # Update post status
        post.status = "published"
        post.published_at = datetime.utcnow()
        post.published_platforms = platforms
        db.commit()
        
        # Log publication action
        log_entry = Log(
            user_id=post.user_id,
            action_category="post_published",
            action_type="publish",
            resource_type="post",
            resource_id=post_id,
            status="success",
            metadata={
                "platforms": platforms,
                "platforms_status": platforms_status,
                "published_urls": published_urls,
            }
        )
        db.add(log_entry)
        db.commit()
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'post_id': post_id,
            'platforms_status': platforms_status,
        })
        
        logger.info(f"Post {post_id} published successfully")
        
        return {
            "post_id": post_id,
            "platforms_status": platforms_status,
            "published_urls": published_urls,
            "published_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Post publishing failed: {str(e)}", exc_info=True)
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise
        
    finally:
        db.close()


# ============================================================================
# Scheduled Publishing Task
# ============================================================================

@shared_task(bind=True, name='app.tasks.publish_tasks.publish_scheduled_post')
def publish_scheduled_post(self, schedule_id: int):
    """
    Publish a scheduled post at its scheduled time.
    
    Called by Celery Beat at scheduled time.
    
    Args:
        schedule_id: Schedule ID to publish
    
    Returns:
        dict: Publication results
    """
    db = SessionLocal()
    
    try:
        self.update_state(state='PROCESSING', meta={'progress': 10})
        
        # Get schedule
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            raise ValueError(f"Schedule {schedule_id} not found")
        
        post = db.query(Post).filter(Post.id == schedule.post_id).first()
        if not post:
            raise ValueError(f"Post {schedule.post_id} not found")
        
        logger.info(f"Publishing scheduled post {post.id} to {schedule.platform}")
        
        self.update_state(state='PROCESSING', meta={'progress': 40})
        
        # Get account
        account = db.query(Account).filter(
            Account.id == schedule.account_id
        ).first()
        
        if not account:
            raise ValueError(f"Account {schedule.account_id} not found")
        
        # Simulate platform API call
        time.sleep(1)
        
        # Mock publication
        url = _publish_to_platform(post, account, schedule.platform)
        
        self.update_state(state='PROCESSING', meta={'progress': 70})
        
        # Update schedule and post
        schedule.status = "published"
        schedule.published_url = url
        schedule.published_at = datetime.utcnow()
        
        post.published_at = datetime.utcnow()
        if not post.published_platforms:
            post.published_platforms = []
        if schedule.platform not in post.published_platforms:
            post.published_platforms.append(schedule.platform)
        
        db.commit()
        
        # Log action
        log_entry = Log(
            user_id=post.user_id,
            action_category="post_published",
            action_type="scheduled_publish",
            resource_type="schedule",
            resource_id=schedule_id,
            status="success",
            metadata={
                "post_id": post.id,
                "platform": schedule.platform,
                "published_url": url,
            }
        )
        db.add(log_entry)
        db.commit()
        
        self.update_state(state='SUCCESS', meta={'progress': 100})
        
        logger.info(f"Scheduled post published: {post.id}")
        
        return {
            "schedule_id": schedule_id,
            "post_id": post.id,
            "platform": schedule.platform,
            "published_url": url,
            "published_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Scheduled publish failed: {str(e)}", exc_info=True)
        
        # Update schedule status to failed
        try:
            schedule.status = "failed"
            schedule.errors = str(e)
            db.commit()
        except:
            pass
        
        raise
        
    finally:
        db.close()


# ============================================================================
# Bulk Publishing Task
# ============================================================================

@shared_task(bind=True, name='app.tasks.publish_tasks.publish_bulk')
def publish_bulk(self, post_ids: list, platforms: list):
    """
    Publish multiple posts in bulk.
    
    Args:
        post_ids: List of post IDs to publish
        platforms: List of platforms to publish to
    
    Returns:
        dict: Results for all posts
    """
    results = []
    
    try:
        total_posts = len(post_ids)
        
        for idx, post_id in enumerate(post_ids):
            progress = int((idx / total_posts) * 100)
            self.update_state(state='PROCESSING', meta={
                'progress': progress,
                'current_post': post_id,
                'completed': idx,
                'total': total_posts,
            })
            
            # Publish each post
            result = publish_post.apply_async(args=[post_id, platforms])
            results.append({
                "post_id": post_id,
                "task_id": result.id,
                "status": result.status,
            })
        
        logger.info(f"Bulk publishing completed: {len(post_ids)} posts")
        
        return {
            "bulk_task_id": self.request.id,
            "total_posts": total_posts,
            "results": results,
            "published_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Bulk publishing failed: {str(e)}", exc_info=True)
        raise


# ============================================================================
# Retry Failed Publishes
# ============================================================================

@shared_task(bind=True, name='app.tasks.publish_tasks.retry_failed_publishes')
def retry_failed_publishes(self, limit: int = 10):
    """
    Retry publishing for failed schedules.
    
    Args:
        limit: Maximum number of retries to attempt
    
    Returns:
        dict: Retry results
    """
    db = SessionLocal()
    
    try:
        # Get failed schedules
        failed_schedules = db.query(Schedule).filter(
            Schedule.status == "failed",
            Schedule.retry_count < 3
        ).limit(limit).all()
        
        logger.info(f"Retrying {len(failed_schedules)} failed publishes")
        
        results = []
        for schedule in failed_schedules:
            try:
                # Increment retry count
                schedule.retry_count = (schedule.retry_count or 0) + 1
                db.commit()
                
                # Retry publishing
                result = publish_scheduled_post.apply_async(args=[schedule.id])
                results.append({
                    "schedule_id": schedule.id,
                    "task_id": result.id,
                    "retry_attempt": schedule.retry_count,
                })
                
            except Exception as e:
                logger.error(f"Retry failed for schedule {schedule.id}: {str(e)}")
        
        logger.info(f"Retry publishing completed: {len(results)} attempts")
        
        return {
            "total_retried": len(results),
            "results": results,
            "retried_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Retry publishing failed: {str(e)}", exc_info=True)
        raise
        
    finally:
        db.close()


# ============================================================================
# Helper Functions
# ============================================================================

def _publish_to_platform(post: Post, account: Account, platform: str) -> str:
    """
    Publish to specific platform.
    
    Mock implementation - replace with actual platform APIs.
    
    Args:
        post: Post object
        account: Account object
        platform: Platform name
    
    Returns:
        str: Published content URL
    """
    platform_urls = {
        "instagram": f"https://instagram.com/reel/{random.randint(1000000, 9999999)}",
        "tiktok": f"https://tiktok.com/@user/video/{random.randint(1000000, 9999999999)}",
        "youtube": f"https://youtube.com/watch?v={random.randint(1000000000, 9999999999)}",
        "facebook": f"https://facebook.com/user/posts/{random.randint(1000000000, 9999999999)}",
        "x": f"https://x.com/user/status/{random.randint(1000000000000000000, 9999999999999999999)}",
        "linkedin": f"https://linkedin.com/feed/update/urn:li:activity:{random.randint(1000000000000000000, 9999999999999999999)}/",
        "pinterest": f"https://pinterest.com/pin/{random.randint(1000000000000000000, 9999999999999999999)}/",
        "telegram": f"https://t.me/channel/{random.randint(1, 9999)}",
    }
    
    return platform_urls.get(platform.lower(), f"https://{platform}.com/post/{random.randint(1000, 9999)}")
