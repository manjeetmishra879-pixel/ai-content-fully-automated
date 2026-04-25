"""
SQLAlchemy Models Usage Guide & Examples

This file demonstrates how to use the ORM models in the AI Content Platform.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from app.models import (
    User, Account, Post, Analytics, Trend, Hashtag, Asset,
    Schedule, Duplicate, Campaign, Log,
    UserPlan, SubscriptionStatus, Platform, PostStatus, ContentType,
    ProcessingStatus, ScheduleStatus, DuplicateAction, LogStatus
)


# =====================================================================
# USER OPERATIONS
# =====================================================================

class UserOperations:
    """User management operations"""
    
    @staticmethod
    def create_user(
        db: Session,
        email: str,
        username: str,
        password_hash: str,
        first_name: str = None,
        last_name: str = None,
        plan: str = UserPlan.FREE.value,
    ) -> User:
        """Create a new user"""
        user = User(
            email=email,
            username=username,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            plan=plan,
            subscription_status=SubscriptionStatus.ACTIVE.value,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """Get user by username"""
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_active_users(db: Session, limit: int = 100) -> List[User]:
        """Get all active users"""
        return db.query(User).filter(User.is_active == True).limit(limit).all()
    
    @staticmethod
    def update_user(db: Session, user_id: int, **kwargs) -> User:
        """Update user fields"""
        user = db.query(User).get(user_id)
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            db.commit()
            db.refresh(user)
        return user


# =====================================================================
# ACCOUNT OPERATIONS
# =====================================================================

class AccountOperations:
    """Social media account operations"""
    
    @staticmethod
    def create_account(
        db: Session,
        user_id: int,
        platform: str,
        platform_user_id: str,
        username: str,
        access_token: str,
        **kwargs
    ) -> Account:
        """Create a new social media account"""
        account = Account(
            user_id=user_id,
            platform=platform,
            platform_user_id=platform_user_id,
            username=username,
            access_token=access_token,
            **kwargs
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        return account
    
    @staticmethod
    def get_user_accounts(db: Session, user_id: int) -> List[Account]:
        """Get all accounts for a user"""
        return db.query(Account).filter(
            Account.user_id == user_id,
            Account.deleted_at == None
        ).all()
    
    @staticmethod
    def get_platform_accounts(
        db: Session,
        user_id: int,
        platform: str
    ) -> List[Account]:
        """Get accounts for specific platform"""
        return db.query(Account).filter(
            Account.user_id == user_id,
            Account.platform == platform,
            Account.is_active == True
        ).all()
    
    @staticmethod
    def detect_shadowban(db: Session, account_id: int) -> bool:
        """Check for shadowban indicators"""
        account = db.query(Account).get(account_id)
        if not account:
            return False
        
        # Get recent analytics
        recent_analytics = db.query(Analytics).filter(
            Analytics.account_id == account_id,
            Analytics.tracked_at > datetime.utcnow() - timedelta(days=7)
        ).all()
        
        if not recent_analytics:
            return False
        
        # Check for engagement drop >70%
        avg_engagement = sum(a.engagement_rate for a in recent_analytics) / len(recent_analytics)
        
        if avg_engagement < 0.3:  # 30% drop threshold
            account.is_shadowbanned = True
            account.shadowban_detected_at = datetime.utcnow()
            db.commit()
            return True
        
        return account.is_shadowbanned


# =====================================================================
# POST OPERATIONS
# =====================================================================

class PostOperations:
    """Content post operations"""
    
    @staticmethod
    def create_post(
        db: Session,
        user_id: int,
        title: str,
        script: str,
        category: str,
        content_type: str,
        **kwargs
    ) -> Post:
        """Create a new post"""
        post = Post(
            user_id=user_id,
            title=title,
            script=script,
            category=category,
            content_type=content_type,
            status=PostStatus.DRAFT.value,
            **kwargs
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        return post
    
    @staticmethod
    def get_user_posts(
        db: Session,
        user_id: int,
        status: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Post]:
        """Get user's posts"""
        query = db.query(Post).filter(User.id == user_id)
        if status:
            query = query.filter(Post.status == status)
        return query.order_by(desc(Post.created_at)).limit(limit).offset(offset).all()
    
    @staticmethod
    def get_draft_posts(db: Session, user_id: int) -> List[Post]:
        """Get draft posts"""
        return db.query(Post).filter(
            Post.user_id == user_id,
            Post.status == PostStatus.DRAFT.value
        ).all()
    
    @staticmethod
    def publish_post(db: Session, post_id: int, platforms: List[str]) -> Post:
        """Publish post to platforms"""
        post = db.query(Post).get(post_id)
        if post:
            post.status = PostStatus.PUBLISHED.value
            post.published_at = datetime.utcnow()
            post.platforms = {p: {'status': 'published'} for p in platforms}
            db.commit()
            db.refresh(post)
        return post
    
    @staticmethod
    def add_hashtags_to_post(db: Session, post_id: int, hashtag_ids: List[int]):
        """Add hashtags to post"""
        post = db.query(Post).get(post_id)
        if post:
            hashtags = db.query(Hashtag).filter(Hashtag.id.in_(hashtag_ids)).all()
            post.hashtags.extend(hashtags)
            db.commit()


# =====================================================================
# ANALYTICS OPERATIONS
# =====================================================================

class AnalyticsOperations:
    """Content performance analytics operations"""
    
    @staticmethod
    def track_post_performance(
        db: Session,
        post_id: int,
        account_id: int,
        platform: str,
        views: int = 0,
        likes: int = 0,
        comments: int = 0,
        shares: int = 0,
        **kwargs
    ) -> Analytics:
        """Track post performance metrics"""
        
        # Calculate engagement rate
        total_engagement = likes + comments + shares
        engagement_rate = (total_engagement / views * 100) if views > 0 else 0.0
        
        analytics = Analytics(
            post_id=post_id,
            account_id=account_id,
            platform=platform,
            views=views,
            likes=likes,
            comments=comments,
            shares=shares,
            engagement_rate=engagement_rate,
            **kwargs
        )
        db.add(analytics)
        db.commit()
        db.refresh(analytics)
        return analytics
    
    @staticmethod
    def get_post_analytics(db: Session, post_id: int) -> List[Analytics]:
        """Get all analytics for a post"""
        return db.query(Analytics).filter(
            Analytics.post_id == post_id
        ).order_by(desc(Analytics.tracked_at)).all()
    
    @staticmethod
    def get_platform_performance(
        db: Session,
        account_id: int,
        platform: str,
        days: int = 30
    ) -> dict:
        """Get platform performance summary"""
        since = datetime.utcnow() - timedelta(days=days)
        
        analytics = db.query(Analytics).filter(
            Analytics.account_id == account_id,
            Analytics.platform == platform,
            Analytics.tracked_at >= since
        ).all()
        
        if not analytics:
            return {}
        
        return {
            'total_views': sum(a.views for a in analytics),
            'total_likes': sum(a.likes for a in analytics),
            'total_comments': sum(a.comments for a in analytics),
            'avg_engagement_rate': sum(a.engagement_rate for a in analytics) / len(analytics),
            'post_count': len(set(a.post_id for a in analytics)),
        }


# =====================================================================
# TREND OPERATIONS
# =====================================================================

class TrendOperations:
    """Trend management operations"""
    
    @staticmethod
    def create_trend(
        db: Session,
        title: str,
        trend_score: float,
        viral_score: float,
        source: str,
        **kwargs
    ) -> Trend:
        """Create a new trend"""
        trend = Trend(
            title=title,
            trend_score=trend_score,
            viral_score=viral_score,
            source=source,
            is_active=True,
            **kwargs
        )
        db.add(trend)
        db.commit()
        db.refresh(trend)
        return trend
    
    @staticmethod
    def get_trending_topics(db: Session, limit: int = 20) -> List[Trend]:
        """Get top trending topics"""
        return db.query(Trend).filter(
            Trend.is_active == True
        ).order_by(desc(Trend.trend_score)).limit(limit).all()
    
    @staticmethod
    def get_rising_trends(db: Session, limit: int = 10) -> List[Trend]:
        """Get rising fast trends"""
        return db.query(Trend).filter(
            Trend.is_active == True,
            Trend.is_rising == True
        ).order_by(desc(Trend.growth_rate)).limit(limit).all()


# =====================================================================
# SCHEDULE OPERATIONS
# =====================================================================

class ScheduleOperations:
    """Publishing schedule operations"""
    
    @staticmethod
    def create_schedule(
        db: Session,
        user_id: int,
        account_id: int,
        post_id: int,
        platform: str,
        scheduled_time: datetime,
        **kwargs
    ) -> Schedule:
        """Create publishing schedule"""
        schedule = Schedule(
            user_id=user_id,
            account_id=account_id,
            post_id=post_id,
            platform=platform,
            scheduled_time=scheduled_time,
            status=ScheduleStatus.PENDING.value,
            **kwargs
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule
    
    @staticmethod
    def get_pending_schedules(db: Session) -> List[Schedule]:
        """Get schedules pending publishing"""
        now = datetime.utcnow()
        return db.query(Schedule).filter(
            Schedule.status == ScheduleStatus.PENDING.value,
            Schedule.scheduled_time <= now
        ).all()
    
    @staticmethod
    def mark_as_published(
        db: Session,
        schedule_id: int,
        published_url: str = None,
        platform_response: dict = None
    ) -> Schedule:
        """Mark schedule as published"""
        schedule = db.query(Schedule).get(schedule_id)
        if schedule:
            schedule.status = ScheduleStatus.PUBLISHED.value
            schedule.published_at = datetime.utcnow()
            if published_url:
                schedule.published_url = published_url
            if platform_response:
                schedule.platform_response = platform_response
            db.commit()
            db.refresh(schedule)
        return schedule


# =====================================================================
# DUPLICATE DETECTION OPERATIONS
# =====================================================================

class DuplicateOperations:
    """Duplicate content detection operations"""
    
    @staticmethod
    def mark_duplicate(
        db: Session,
        primary_post_id: int,
        duplicate_post_id: int,
        similarity_score: float,
        detection_method: str,
        action: str = DuplicateAction.WARNING.value,
        **kwargs
    ) -> Duplicate:
        """Mark content as duplicate"""
        duplicate = Duplicate(
            primary_post_id=primary_post_id,
            duplicate_post_id=duplicate_post_id,
            similarity_score=similarity_score,
            detection_method=detection_method,
            action=action,
            **kwargs
        )
        db.add(duplicate)
        db.commit()
        db.refresh(duplicate)
        return duplicate
    
    @staticmethod
    def find_duplicates(db: Session, post_id: int) -> List[Duplicate]:
        """Find duplicate records for a post"""
        return db.query(Duplicate).filter(
            or_(
                Duplicate.primary_post_id == post_id,
                Duplicate.duplicate_post_id == post_id
            )
        ).all()


# =====================================================================
# CAMPAIGN OPERATIONS
# =====================================================================

class CampaignOperations:
    """Marketing campaign operations"""
    
    @staticmethod
    def create_campaign(
        db: Session,
        user_id: int,
        name: str,
        start_date: datetime,
        end_date: datetime,
        objective: str,
        **kwargs
    ) -> Campaign:
        """Create a new campaign"""
        campaign = Campaign(
            user_id=user_id,
            name=name,
            start_date=start_date,
            end_date=end_date,
            objective=objective,
            status='draft',
            **kwargs
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        return campaign
    
    @staticmethod
    def get_active_campaigns(db: Session, user_id: int) -> List[Campaign]:
        """Get active campaigns for user"""
        now = datetime.utcnow()
        return db.query(Campaign).filter(
            Campaign.user_id == user_id,
            Campaign.start_date <= now,
            Campaign.end_date >= now,
            Campaign.status == 'active'
        ).all()
    
    @staticmethod
    def calculate_campaign_roi(db: Session, campaign_id: int) -> float:
        """Calculate campaign ROI"""
        campaign = db.query(Campaign).get(campaign_id)
        if not campaign or not campaign.budget:
            return 0.0
        
        # ROI = (conversions * value - spent) / spent * 100
        # Simplified: ROI = spent / budget * 100
        return min((campaign.spent / campaign.budget * 100), 100.0)


# =====================================================================
# LOGGING OPERATIONS
# =====================================================================

class LoggingOperations:
    """Audit logging operations"""
    
    @staticmethod
    def log_action(
        db: Session,
        user_id: int,
        entity_type: str,
        entity_id: int,
        action: str,
        description: str = None,
        old_values: dict = None,
        new_values: dict = None,
        status: str = LogStatus.SUCCESS.value,
        **kwargs
    ) -> Log:
        """Log user action"""
        log = Log(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            action_category='user_action',
            description=description,
            old_values=old_values or {},
            new_values=new_values or {},
            status=status,
            **kwargs
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
    
    @staticmethod
    def get_user_activity(db: Session, user_id: int, days: int = 7) -> List[Log]:
        """Get user's activity log"""
        since = datetime.utcnow() - timedelta(days=days)
        return db.query(Log).filter(
            Log.user_id == user_id,
            Log.created_at >= since
        ).order_by(desc(Log.created_at)).all()
    
    @staticmethod
    def log_error(
        db: Session,
        user_id: int,
        entity_type: str,
        error_message: str,
        error_code: str = None,
        **kwargs
    ) -> Log:
        """Log error"""
        return LoggingOperations.log_action(
            db=db,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=0,
            action='error',
            description=error_message,
            status=LogStatus.FAILURE.value,
            error_code=error_code,
            **kwargs
        )


# =====================================================================
# USAGE EXAMPLES
# =====================================================================

def example_user_flow(db: Session):
    """Example: Create user, add account, create post"""
    
    # Create user
    user = UserOperations.create_user(
        db,
        email='creator@example.com',
        username='content_creator',
        password_hash='hashed_pass',
        plan=UserPlan.PRO.value,
    )
    print(f"Created user: {user.username}")
    
    # Create account
    account = AccountOperations.create_account(
        db,
        user_id=user.id,
        platform=Platform.INSTAGRAM.value,
        platform_user_id='123456',
        username='content_creator',
        access_token='token_here',
    )
    print(f"Created account: @{account.username} on {account.platform}")
    
    # Create post
    post = PostOperations.create_post(
        db,
        user_id=user.id,
        account_id=account.id,
        title='My First Viral Post',
        script='Content script here...',
        category='motivation',
        content_type=ContentType.REEL.value,
    )
    print(f"Created post: {post.title}")
    
    # Add hashtags
    hashtag = db.query(Hashtag).first()
    if hashtag:
        PostOperations.add_hashtags_to_post(db, post.id, [hashtag.id])
        print(f"Added hashtag: #{hashtag.tag}")
    
    # Create schedule
    from datetime import datetime, timedelta
    schedule_time = datetime.utcnow() + timedelta(hours=2)
    schedule = ScheduleOperations.create_schedule(
        db,
        user_id=user.id,
        account_id=account.id,
        post_id=post.id,
        platform=Platform.INSTAGRAM.value,
        scheduled_time=schedule_time,
    )
    print(f"Scheduled post: {schedule.scheduled_time}")


if __name__ == "__main__":
    print("Models Usage Guide - See examples in this file")
