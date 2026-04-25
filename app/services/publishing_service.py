"""
Content publishing service
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.models import Content, Post, Schedule, Account
from app.engines import get_engine


class PublishingService:
    """Service for managing content publishing"""

    def __init__(self, db: Session, redis_client=None):
        self.db = db
        self.redis = redis_client
        self.publisher_engine = get_engine("publisher")
        self.scheduler_engine = get_engine("scheduler")

    async def publish_now(self, content_id: int, platforms: List[str], user_id: int,
                         media: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Publish content immediately to specified platforms"""
        content = self.db.query(Content).filter(
            Content.id == content_id,
            Content.user_id == user_id
        ).first()

        if not content:
            raise ValueError(f"Content {content_id} not found")

        # Create Post record
        post = Post(
            user_id=user_id,
            content_id=content_id,
            title=content.title,
            script=content.script,
            caption=content.script,  # Use script as base caption
            platforms=platforms,
            hashtags=content.hashtags,
            ctas=content.ctas,
            extra_metadata=content.extra_metadata,
            status="publishing"
        )

        self.db.add(post)
        self.db.commit()
        self.db.refresh(post)

        # Publish using publisher engine
        result = self.publisher_engine.run(
            db=self.db,
            user_id=user_id,
            post_id=post.id,
            platforms=platforms,
            media=media
        )

        # Update post with results
        post.status = "published" if all(r.get("published", False) for r in result.get("results", [])) else "failed"
        post.platforms_meta = result
        self.db.commit()

        return {
            "post_id": post.id,
            "status": post.status,
            "results": result.get("results", [])
        }

    async def schedule_publishing(self, content_id: int, platforms: List[str],
                                schedule_time: datetime, user_id: int) -> Dict[str, Any]:
        """Schedule content for publishing at a specific time"""
        content = self.db.query(Content).filter(
            Content.id == content_id,
            Content.user_id == user_id
        ).first()

        if not content:
            raise ValueError(f"Content {content_id} not found")

        # Create Post record
        post = Post(
            user_id=user_id,
            content_id=content_id,
            title=content.title,
            script=content.script,
            caption=content.script,
            platforms=platforms,
            hashtags=content.hashtags,
            ctas=content.ctas,
            extra_metadata=content.extra_metadata,
            status="scheduled"
        )

        self.db.add(post)
        self.db.commit()
        self.db.refresh(post)

        # Schedule using scheduler engine
        schedule_result = self.scheduler_engine.run(
            action="schedule",
            db=self.db,
            user_id=user_id,
            post_id=post.id,
            platform=platforms[0],  # Primary platform for scheduling
            scheduled_at=schedule_time
        )

        return {
            "post_id": post.id,
            "schedule_id": schedule_result.get("id"),
            "scheduled_time": schedule_result.get("scheduled_time"),
            "status": "scheduled"
        }

    async def get_schedule(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user's publishing schedule"""
        return self.scheduler_engine.run(action="list", db=self.db, user_id=user_id)

    async def cancel_schedule(self, schedule_id: int, user_id: int) -> bool:
        """Cancel a scheduled post"""
        # Verify ownership through post
        schedule = self.db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            return False

        post = self.db.query(Post).filter(
            Post.id == schedule.post_id,
            Post.user_id == user_id
        ).first()

        if not post:
            return False

        return self.scheduler_engine.run(action="cancel", db=self.db, schedule_id=schedule_id)

    async def get_post_status(self, post_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get publishing status of a post"""
        post = self.db.query(Post).filter(
            Post.id == post_id,
            Post.user_id == user_id
        ).first()

        if not post:
            return None

        return {
            "id": post.id,
            "status": post.status,
            "platforms_meta": post.platforms_meta,
            "platform_post_ids": post.platform_post_ids,
            "published_at": post.published_at.isoformat() if post.published_at else None,
            "created_at": post.created_at.isoformat() if post.created_at else None
        }

    async def retry_failed_post(self, post_id: int, user_id: int) -> Dict[str, Any]:
        """Retry publishing a failed post"""
        post = self.db.query(Post).filter(
            Post.id == post_id,
            Post.user_id == user_id,
            Post.status == "failed"
        ).first()

        if not post:
            raise ValueError(f"Failed post {post_id} not found")

        # Reset status and try again
        post.status = "publishing"
        self.db.commit()

        result = self.publisher_engine.run(
            db=self.db,
            user_id=user_id,
            post_id=post.id,
            platforms=post.platforms or []
        )

        post.status = "published" if all(r.get("published", False) for r in result.get("results", [])) else "failed"
        post.platforms_meta = result
        self.db.commit()

        return {
            "post_id": post.id,
            "status": post.status,
            "results": result.get("results", [])
        }
