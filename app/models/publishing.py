"""
Publishing schedule model
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from app.core.database import Base

class PublishingSchedule(Base):
    __tablename__ = "publishing_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, index=True)
    platform = Column(String(50), index=True)
    scheduled_time = Column(DateTime(timezone=True), index=True)
    published_time = Column(DateTime(timezone=True), nullable=True)
    is_published = Column(Boolean, default=False)
    metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    class Config:
        from_attributes = True
