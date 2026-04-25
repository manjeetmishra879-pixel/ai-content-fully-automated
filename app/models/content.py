"""
Content model for storing generated content
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Enum
from sqlalchemy.sql import func
from app.core.database import Base
from enum import Enum as PyEnum

class ContentStatus(str, PyEnum):
    DRAFT = "draft"
    GENERATED = "generated"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class Content(Base):
    __tablename__ = "contents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True)
    script = Column(Text)
    hooks = Column(JSON)
    captions = Column(JSON)
    hashtags = Column(JSON)
    category = Column(String(50), index=True)
    platform_targets = Column(JSON)
    quality_score = Column(Float, default=0.0)
    engagement_prediction = Column(Float, default=0.0)
    status = Column(Enum(ContentStatus), default=ContentStatus.DRAFT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    class Config:
        from_attributes = True
