"""
API v1 analytics endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random

from app.core.database import get_db
from app.models import Post, Analytics, Account, Hashtag, User
from app.schemas import (
    AnalyticsRequest,
    AnalyticsResponse,
    PostAnalytics,
    PerformanceMetrics,
    InsightRequest,
    InsightResponse,
    ErrorResponse
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ============================================================================
# Mock Analytics Data (Replace with real data aggregation)
# ============================================================================

def generate_mock_analytics(post_id: int, platform: str) -> PostAnalytics:
    """Generate mock analytics data for demonstration."""
    return PostAnalytics(
        post_id=post_id,
        platform=platform,
        views=random.randint(100, 50000),
        likes=random.randint(10, 5000),
        comments=random.randint(0, 1000),
        shares=random.randint(0, 500),
        saves=random.randint(0, 2000),
        engagement_rate=round(random.uniform(1.0, 15.0), 2),
        reach=random.randint(100, 40000),
        impressions=random.randint(500, 100000),
        click_through_rate=round(random.uniform(0.5, 5.0), 2),
        video_completion_rate=round(random.uniform(20, 95), 1),
        timestamp=datetime.utcnow()
    )


# ============================================================================
# Analytics Routes
# ============================================================================

@router.post("/posts/{post_id}", response_model=AnalyticsResponse)
async def get_post_analytics(
    post_id: int,
    user_id: int = Depends(lambda: 1),  # TODO: Extract from auth token
    db: Session = Depends(get_db)
) -> AnalyticsResponse:
    """
    Get analytics for a specific post.
    
    **Parameters:**
    - post_id: Post to get analytics for
    
    **Returns:** Detailed analytics including engagement, reach, and performance metrics
    """
    
    # Verify post exists and belongs to user
    post = db.query(Post).filter(
        Post.id == post_id,
        Post.user_id == user_id
    ).first()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Fetch post analytics from database
    analytics = db.query(Analytics).filter(
        Analytics.post_id == post_id
    ).order_by(Analytics.timestamp.desc()).limit(100).all()
    
    # Convert to response format
    data_points = [
        PostAnalytics(
            post_id=a.post_id,
            platform=a.platform,
            views=a.views,
            likes=a.likes,
            comments=a.comments,
            shares=a.shares,
            saves=a.saves,
            engagement_rate=a.engagement_rate,
            reach=a.reach,
            impressions=a.impressions,
            timestamp=a.timestamp
        ) for a in analytics
    ] or [generate_mock_analytics(post_id, "instagram")]
    
    # Calculate summary
    total_views = sum(dp.views for dp in data_points)
    total_engagement = sum(dp.likes + dp.comments + dp.shares + dp.saves for dp in data_points)
    avg_engagement_rate = sum(dp.engagement_rate for dp in data_points) / len(data_points) if data_points else 0
    
    summary = {
        "total_views": total_views,
        "total_engagement": total_engagement,
        "average_engagement_rate": round(avg_engagement_rate, 2),
        "total_likes": sum(dp.likes for dp in data_points),
        "total_comments": sum(dp.comments for dp in data_points),
        "total_shares": sum(dp.shares for dp in data_points),
        "total_saves": sum(dp.saves for dp in data_points)
    }
    
    return AnalyticsResponse(
        post_id=post_id,
        data_points=data_points,
        summary=summary,
        period="since_publication"
    )


@router.get("/accounts/{account_id}", response_model=PerformanceMetrics)
async def get_account_performance(
    account_id: int,
    user_id: int = Depends(lambda: 1),  # TODO: Extract from auth token
    db: Session = Depends(get_db)
) -> PerformanceMetrics:
    """
    Get performance metrics for a social media account.
    
    **Parameters:**
    - account_id: Account to get metrics for
    
    **Returns:** Account-level performance including engagement rates, top posts, and optimal posting times
    """
    
    # Verify account exists and belongs to user
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == user_id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Get all posts for account
    posts = db.query(Post).filter(
        Post.account_id == account_id
    ).all()
    
    if not posts:
        posts = []
    
    # Calculate metrics
    total_posts = len(posts)
    total_followers = account.followers or 0
    
    # Get analytics for all posts
    all_analytics = db.query(Analytics).filter(
        Analytics.account_id == account_id
    ).all()
    
    avg_engagement = 0
    if all_analytics:
        avg_engagement = sum(a.engagement_rate for a in all_analytics) / len(all_analytics)
    
    # Find top performing post
    top_post = None
    if posts:
        top_post_analytics = db.query(Analytics).filter(
            Analytics.post_id.in_([p.id for p in posts])
        ).order_by(Analytics.views.desc()).first()
        
        if top_post_analytics:
            top_post = top_post_analytics.post_id
    
    # Mock optimal posting times (replace with real analysis)
    optimal_times = ["09:00", "13:00", "19:00", "21:00"]
    
    return PerformanceMetrics(
        account_id=account_id,
        platform=account.platform,
        total_posts=total_posts,
        total_followers=total_followers,
        average_engagement_rate=round(avg_engagement, 2),
        top_performing_post_id=top_post,
        hashtag_performance={
            "#code": 4.5,
            "#python": 5.2,
            "#development": 3.8,
            "#tech": 6.1
        },
        optimal_posting_times=optimal_times,
        audience_demographics={
            "age_groups": {"18-24": 35, "25-34": 45, "35-44": 15, "45+": 5},
            "gender": {"male": 55, "female": 45},
            "top_countries": ["US", "UK", "CA", "AU"]
        }
    )


@router.get("/compare")
async def compare_accounts(
    account_ids: list[int] = Query(..., description="List of account IDs to compare"),
    user_id: int = Depends(lambda: 1),  # TODO: Extract from auth token
    db: Session = Depends(get_db)
):
    """
    Compare performance metrics across multiple accounts.
    
    **Parameters:**
    - account_ids: List of account IDs to compare (query parameter, can be repeated)
    
    **Returns:** Comparative metrics across accounts
    """
    
    # Verify all accounts belong to user
    accounts = db.query(Account).filter(
        Account.id.in_(account_ids),
        Account.user_id == user_id
    ).all()
    
    if len(accounts) != len(account_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more accounts not found"
        )
    
    comparison_data = []
    
    for account in accounts:
        metrics = {
            "account_id": account.id,
            "platform": account.platform,
            "followers": account.followers or 0,
            "engagement_rate": account.engagement_rate or 0,
            "posts_count": len(db.query(Post).filter(Post.account_id == account.id).all())
        }
        comparison_data.append(metrics)
    
    return {
        "accounts_compared": len(accounts),
        "data": comparison_data,
        "timestamp": datetime.utcnow()
    }


@router.post("/insights")
async def generate_insights(
    request: InsightRequest,
    user_id: int = Depends(lambda: 1),  # TODO: Extract from auth token
    db: Session = Depends(get_db)
) -> InsightResponse:
    """
    Generate AI-powered insights based on account analytics.
    
    **Parameters:**
    - account_id: Account to analyze
    - period: Analysis period (week, month, quarter, year)
    - focus_area: Focus area (engagement, growth, audience, content, trends)
    
    **Returns:** AI-generated insights and recommendations
    """
    
    # Verify account exists and belongs to user
    account = db.query(Account).filter(
        Account.id == request.account_id,
        Account.user_id == user_id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Mock AI insights (replace with real AI service)
    insights_by_area = {
        "engagement": {
            "key_findings": [
                "Your engagement rate is 12% higher than platform average",
                "Posts between 9-12 AM get 30% more engagement",
                "Carousel posts outperform single images by 45%"
            ],
            "recommendations": [
                "Schedule posts for 9-12 AM window for maximum reach",
                "Create more carousel content in your content strategy",
                "Increase posting frequency to 3-4 times per week"
            ]
        },
        "growth": {
            "key_findings": [
                "Follower growth increased 25% in the last week",
                "Collaborations drive 3x more new followers",
                "Hashtag strategy is converting 8.5% of reach to followers"
            ],
            "recommendations": [
                "Plan 2-3 collaborations per month with similar creators",
                "Optimize hashtag mix to include 2-3 trending tags per post",
                "Cross-promote on other platforms to accelerate growth"
            ]
        },
        "audience": {
            "key_findings": [
                "Primary audience is 25-34 year olds (55% of followers)",
                "Female audience engagement is 40% higher",
                "US and UK account for 65% of audience"
            ],
            "recommendations": [
                "Create content specifically tailored to 25-34 demographic",
                "Increase focus on topics that resonate with female audience",
                "Plan content for peak times in US/UK timezones"
            ]
        },
        "content": {
            "key_findings": [
                "Educational content gets 60% more saves",
                "Storytelling format has highest engagement",
                "Videos outperform static content by 3x"
            ],
            "recommendations": [
                "Shift 40% of content strategy to educational material",
                "Incorporate personal storytelling in 50% of posts",
                "Prioritize video content in content calendar"
            ]
        },
        "trends": {
            "key_findings": [
                "You're leveraging trending topics 40% more than peers",
                "Trending content has 5x higher virality potential",
                "Early adoption of trends increases engagement 3x"
            ],
            "recommendations": [
                "Set up trend alerts to catch emerging topics early",
                "Allocate time for rapid content creation around trends",
                "Build a trend database specific to your niche"
            ]
        }
    }
    
    focus = request.focus_area or "engagement"
    insight_data = insights_by_area.get(focus, insights_by_area["engagement"])
    
    return InsightResponse(
        account_id=request.account_id,
        period=request.period,
        key_findings=insight_data["key_findings"],
        recommendations=insight_data["recommendations"],
        ai_summary=f"Based on {request.period} data, your {focus} metrics show positive trends. "
                  f"Focus on following the recommendations to maximize growth.",
        generated_at=datetime.utcnow()
    )


@router.get("/trending-hashtags")
async def get_trending_hashtags(
    account_id: int,
    limit: int = Query(10, ge=1, le=50),
    user_id: int = Depends(lambda: 1),  # TODO: Extract from auth token
    db: Session = Depends(get_db)
):
    """
    Get trending hashtags for an account.
    
    **Parameters:**
    - account_id: Account to get hashtags for
    - limit: Number of hashtags to return
    
    **Returns:** Trending hashtags with performance metrics
    """
    
    # Verify account exists
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == user_id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Get trending hashtags
    hashtags = db.query(Hashtag).filter(
        Hashtag.platform == account.platform
    ).order_by(
        Hashtag.trending_rank.asc() if Hashtag.trending_rank else Hashtag.usage_count.desc()
    ).limit(limit).all()
    
    if not hashtags:
        # Return mock data
        return {
            "account_id": account_id,
            "hashtags": [
                {
                    "hashtag": f"#{name}",
                    "rank": i+1,
                    "usage_count": random.randint(100000, 10000000),
                    "engagement_potential": round(random.uniform(3.0, 12.0), 2),
                    "growth_rate": round(random.uniform(1.0, 25.0), 2),
                    "recommendation": "high" if i < 3 else "medium"
                } for i, name in enumerate(["trending", "content", "creator", "viral", "foryou", "explore", "reels", "shorts", "tiktok", "youtube"])[:limit]
            ]
        }
    
    return {
        "account_id": account_id,
        "hashtags": [
            {
                "hashtag": h.name,
                "rank": h.trending_rank or i+1,
                "usage_count": h.usage_count or 0,
                "engagement_potential": h.engagement_potential or 0,
                "growth_rate": h.growth_rate or 0,
                "recommendation": "high" if i < 3 else "medium"
            } for i, h in enumerate(hashtags)
        ]
    }
