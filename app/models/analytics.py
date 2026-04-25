"""
Analytics model for tracking content performance
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, JSON
from sqlalchemy.sql import func
from app.core.database import Base

class Analytics(Base):
    __tablename__ = "analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, index=True)
    platform_post_id = Column(String(255), unique=True)
    platform = Column(String(50), index=True)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    watch_time_avg = Column(Float, default=0.0)
    skip_rate = Column(Float, default=0.0)
    ctr = Column(Float, default=0.0)
    engagement_rate = Column(Float, default=0.0)
    metadata = Column(JSON)
    tracked_at = Column(DateTime(timezone=True), server_default=func.now())
    
    class Config:
        from_attributes = True
