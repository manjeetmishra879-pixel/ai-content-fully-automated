"""
Content request/response schemas
"""

from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class ContentCreate(BaseModel):
    """Schema for creating content"""
    title: str
    category: str
    platform_targets: List[str]
    
class ContentUpdate(BaseModel):
    """Schema for updating content"""
    title: Optional[str] = None
    script: Optional[str] = None
    hooks: Optional[List[str]] = None
    captions: Optional[List[str]] = None
    hashtags: Optional[List[str]] = None
    
class ContentResponse(BaseModel):
    """Schema for content response"""
    id: int
    title: str
    category: str
    quality_score: float
    engagement_prediction: float
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True
