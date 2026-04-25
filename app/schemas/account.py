"""
Account schemas
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AccountCreate(BaseModel):
    """Schema for adding account"""
    platform: str
    username: str
    access_token: str
    
class AccountResponse(BaseModel):
    """Schema for account response"""
    id: int
    platform: str
    username: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
