"""
Content creation and management service
"""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.models import Content, Post, User
from app.engines import get_engine


class ContentService:
    """Service for managing content operations"""

    def __init__(self, db: Session, redis_client=None):
        self.db = db
        self.redis = redis_client
        self.content_engine = get_engine("content")

    async def create_content(self, content_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Create new content using the content engine"""
        # Use the content engine to generate content
        generated = self.content_engine.run(
            topic=content_data["topic"],
            content_type=content_data.get("content_type", "reel"),
            platforms=content_data.get("platforms", ["instagram"]),
            tone=content_data.get("tone", "energetic"),
            language=content_data.get("language", "english"),
            hashtag_count=content_data.get("hashtag_count", 10),
            include_cta=content_data.get("include_cta", True),
            trends=content_data.get("trends", [])
        )

        # Create Content record
        content = Content(
            user_id=user_id,
            topic=content_data["topic"],
            content_type=content_data.get("content_type", "reel"),
            title=generated.get("title"),
            script=generated.get("script"),
            platforms=content_data.get("platforms", ["instagram"]),
            tone=content_data.get("tone", "energetic"),
            language=content_data.get("language", "english"),
            hashtags=generated.get("hashtags", []),
            ctas=generated.get("ctas", []),
            extra_metadata={
                "hooks": generated.get("hooks", []),
                "captions": generated.get("captions", {}),
                "quality_score": generated.get("quality_score", 0),
                "virality_potential": generated.get("virality_potential", 0),
                "keywords": generated.get("keywords", []),
                "music_mood": generated.get("music_mood"),
                "thumbnail_concept": generated.get("thumbnail_concept")
            }
        )

        self.db.add(content)
        self.db.commit()
        self.db.refresh(content)

        return self._serialize_content(content)

    async def get_content(self, content_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve content by ID"""
        content = self.db.query(Content).filter(
            Content.id == content_id,
            Content.user_id == user_id
        ).first()

        if not content:
            return None

        return self._serialize_content(content)

    async def list_content(self, user_id: int, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List user's content"""
        contents = self.db.query(Content).filter(
            Content.user_id == user_id
        ).order_by(Content.created_at.desc()).limit(limit).offset(offset).all()

        return [self._serialize_content(c) for c in contents]

    async def update_content(self, content_id: int, updates: Dict[str, Any], user_id: int) -> Optional[Dict[str, Any]]:
        """Update existing content"""
        content = self.db.query(Content).filter(
            Content.id == content_id,
            Content.user_id == user_id
        ).first()

        if not content:
            return None

        # Update allowed fields
        allowed_fields = ["title", "script", "hashtags", "ctas", "extra_metadata"]
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(content, field, value)

        self.db.commit()
        self.db.refresh(content)

        return self._serialize_content(content)

    async def delete_content(self, content_id: int, user_id: int) -> bool:
        """Delete content"""
        content = self.db.query(Content).filter(
            Content.id == content_id,
            Content.user_id == user_id
        ).first()

        if not content:
            return False

        self.db.delete(content)
        self.db.commit()

        return True

    async def regenerate_content(self, content_id: int, user_id: int, **overrides) -> Optional[Dict[str, Any]]:
        """Regenerate content with optional overrides"""
        content = self.db.query(Content).filter(
            Content.id == content_id,
            Content.user_id == user_id
        ).first()

        if not content:
            return None

        # Merge existing data with overrides
        generation_params = {
            "topic": content.topic,
            "content_type": content.content_type,
            "platforms": content.platforms or ["instagram"],
            "tone": content.tone,
            "language": content.language,
            "hashtag_count": len(content.hashtags or []),
            "include_cta": bool(content.ctas),
            "trends": []
        }
        generation_params.update(overrides)

        # Regenerate using engine
        generated = self.content_engine.run(**generation_params)

        # Update content
        content.title = generated.get("title")
        content.script = generated.get("script")
        content.hashtags = generated.get("hashtags", [])
        content.ctas = generated.get("ctas", [])
        content.extra_metadata = {
            "hooks": generated.get("hooks", []),
            "captions": generated.get("captions", {}),
            "quality_score": generated.get("quality_score", 0),
            "virality_potential": generated.get("virality_potential", 0),
            "keywords": generated.get("keywords", []),
            "music_mood": generated.get("music_mood"),
            "thumbnail_concept": generated.get("thumbnail_concept")
        }

        self.db.commit()
        self.db.refresh(content)

        return self._serialize_content(content)

    def _serialize_content(self, content: Content) -> Dict[str, Any]:
        """Serialize content object to dict"""
        return {
            "id": content.id,
            "user_id": content.user_id,
            "topic": content.topic,
            "content_type": content.content_type,
            "title": content.title,
            "script": content.script,
            "platforms": content.platforms,
            "tone": content.tone,
            "language": content.language,
            "hashtags": content.hashtags,
            "ctas": content.ctas,
            "extra_metadata": content.extra_metadata,
            "created_at": content.created_at.isoformat() if content.created_at else None,
            "updated_at": content.updated_at.isoformat() if content.updated_at else None
        }
