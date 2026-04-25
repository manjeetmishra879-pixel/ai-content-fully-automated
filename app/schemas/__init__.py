"""
Pydantic schemas for request/response validation across all API endpoints.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ============================================================================
# Health Check Schemas
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(default="healthy", description="Service status")
    version: str = Field(description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    database: str = Field(default="connected", description="Database connection status")
    cache: str = Field(default="connected", description="Cache (Redis) connection status")


# ============================================================================
# Authentication Schemas
# ============================================================================

class UserRegister(BaseModel):
    """User registration request."""
    email: EmailStr = Field(description="User email address")
    username: str = Field(min_length=3, max_length=50, description="Username (3-50 characters)")
    password: str = Field(min_length=8, description="Password (minimum 8 characters)")
    full_name: Optional[str] = Field(None, max_length=100, description="User full name")
    timezone: str = Field(default="UTC", description="User timezone")


class UserLogin(BaseModel):
    """User login request."""
    email: EmailStr = Field(description="User email address")
    password: str = Field(description="User password")


class TokenResponse(BaseModel):
    """Authentication token response."""
    access_token: str = Field(description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    expires_in: int = Field(description="Token expiration time in seconds")
    user_id: int = Field(description="Authenticated user ID")


class UserResponse(BaseModel):
    """User profile response."""
    id: int
    email: str
    username: str
    full_name: Optional[str]
    plan: str = Field(description="User subscription plan: FREE, PRO, ENTERPRISE")
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


# ============================================================================
# Content Generation Schemas
# ============================================================================

class ContentGenerationRequest(BaseModel):
    """Request for AI content generation."""
    topic: str = Field(min_length=5, max_length=500, description="Content topic or keyword")
    content_type: str = Field(
        description="Type of content: reel, short, carousel, story, post, long_form, live, clip"
    )
    platforms: List[str] = Field(
        min_items=1, 
        description="Target platforms: instagram, tiktok, youtube, facebook, x, linkedin, telegram, pinterest"
    )
    tone: Optional[str] = Field(
        default="professional",
        description="Tone of content: professional, casual, funny, inspirational, educational"
    )
    language: Optional[str] = Field(default="english", description="Content language")
    hashtag_count: Optional[int] = Field(default=5, ge=0, le=30, description="Number of hashtags")
    include_cta: Optional[bool] = Field(default=True, description="Include call-to-action")
    length_preference: Optional[str] = Field(
        default="medium",
        description="Content length: short, medium, long"
    )
    trend_ids: Optional[List[int]] = Field(default=None, description="IDs of trends to incorporate")


class ContentGenerationResponse(BaseModel):
    """Generated content response."""
    id: Optional[int] = Field(None, description="Post ID if saved")
    script: str = Field(description="Main content script/caption")
    title: str = Field(description="Content title")
    hooks: List[str] = Field(description="Opening hooks (3-5)")
    hashtags: List[str] = Field(description="Suggested hashtags")
    ctas: List[str] = Field(description="Call-to-action suggestions")
    captions: Dict[str, str] = Field(description="Platform-specific captions")
    quality_score: Optional[float] = Field(None, ge=0, le=100, description="Content quality score")
    virality_potential: Optional[float] = Field(None, ge=0, le=100, description="Virality prediction")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class TrendRequest(BaseModel):
    """Request for trend-based content suggestions."""
    platform: str = Field(description="Target platform")
    language: Optional[str] = Field(default="english")
    limit: Optional[int] = Field(default=10, ge=1, le=100)


class TrendResponse(BaseModel):
    """Trend suggestion response."""
    id: int
    title: str
    description: str
    growth_rate: float
    saturation_level: str  # low, medium, high
    source: str  # google_trends, youtube, reddit, etc.
    related_hashtags: List[str]
    recommendations: Dict[str, Any]


# ============================================================================
# Publish Schemas
# ============================================================================

class PublishRequest(BaseModel):
    """Request to publish content."""
    post_id: int = Field(description="Post ID to publish")
    platforms: List[str] = Field(
        min_items=1,
        description="Platforms to publish to"
    )
    schedule_time: Optional[datetime] = Field(
        None, 
        description="Schedule publish time (leave blank for immediate)"
    )
    notify_followers: Optional[bool] = Field(default=False, description="Notify followers")


class PublishResponse(BaseModel):
    """Publish operation response."""
    post_id: int
    status: str = Field(description="Status: published, scheduled, processing, failed")
    platforms_status: Dict[str, str] = Field(description="Per-platform publication status")
    published_at: Optional[datetime]
    scheduled_for: Optional[datetime]
    urls: Dict[str, str] = Field(description="Published content URLs per platform")


class ScheduleRequest(BaseModel):
    """Request to schedule content publication."""
    post_id: int
    platform: str
    scheduled_time: datetime = Field(description="Time to publish")
    timezone: str = Field(default="UTC")


class ScheduleResponse(BaseModel):
    """Schedule creation response."""
    id: int
    post_id: int
    platform: str
    scheduled_time: datetime
    status: str = Field(description="pending, processing, published, failed, cancelled")
    created_at: datetime


# ============================================================================
# Analytics Schemas
# ============================================================================

class AnalyticsRequest(BaseModel):
    """Request for analytics data."""
    post_id: Optional[int] = Field(None, description="Get analytics for specific post")
    account_id: Optional[int] = Field(None, description="Get analytics for an account")
    platform: Optional[str] = Field(None, description="Filter by platform")
    date_from: Optional[datetime] = Field(None, description="Start date")
    date_to: Optional[datetime] = Field(None, description="End date")
    metric_type: Optional[str] = Field(
        None,
        description="aggregated, hourly, daily, weekly"
    )


class PostAnalytics(BaseModel):
    """Analytics for a single post."""
    post_id: int
    platform: str
    views: int = Field(default=0, description="Total views")
    likes: int = Field(default=0)
    comments: int = Field(default=0)
    shares: int = Field(default=0)
    saves: int = Field(default=0)
    engagement_rate: float = Field(default=0.0, description="Engagement percentage")
    reach: int = Field(default=0)
    impressions: int = Field(default=0)
    click_through_rate: Optional[float] = Field(None)
    video_completion_rate: Optional[float] = Field(None, description="For video content")
    timestamp: datetime


class AnalyticsResponse(BaseModel):
    """Analytics response with aggregated data."""
    post_id: Optional[int]
    account_id: Optional[int]
    data_points: List[PostAnalytics] = Field(description="Time-series analytics data")
    summary: Dict[str, Any] = Field(
        description="Aggregated summary stats (total views, avg engagement, etc.)"
    )
    period: str = Field(description="Period covered by analytics")


class PerformanceMetrics(BaseModel):
    """Account-level performance metrics."""
    account_id: int
    platform: str
    total_posts: int
    total_followers: int
    average_engagement_rate: float
    top_performing_post_id: Optional[int]
    hashtag_performance: Dict[str, float] = Field(description="Hashtag to performance mapping")
    optimal_posting_times: List[str] = Field(description="Optimal times to post")
    audience_demographics: Dict[str, Any]


class InsightRequest(BaseModel):
    """Request for AI-generated insights."""
    account_id: int
    period: str = Field(default="week", description="week, month, quarter, year")
    focus_area: Optional[str] = Field(
        None,
        description="engagement, growth, audience, content, trends"
    )


class InsightResponse(BaseModel):
    """AI-generated insights response."""
    account_id: int
    period: str
    key_findings: List[str] = Field(description="Main findings")
    recommendations: List[str] = Field(description="Actionable recommendations")
    ai_summary: str = Field(description="AI-generated summary")
    generated_at: datetime


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Error response."""
    error: str = Field(description="Error code")
    message: str = Field(description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Pagination
# ============================================================================

class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: Optional[str] = Field(default="desc", description="asc or desc")


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    data: List[Any]
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool
