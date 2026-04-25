"""
Social media account model
"""

from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from app.core.database import Base

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    platform = Column(String(50), index=True)  # instagram, tiktok, youtube, etc.
    username = Column(String(255))
    account_id = Column(String(255), unique=True)
    access_token = Column(String(1000))
    refresh_token = Column(String(1000), nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    class Config:
        from_attributes = True
