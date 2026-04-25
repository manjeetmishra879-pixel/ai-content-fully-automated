"""
Database initialization script

Usage:
    python scripts/init_db.py create      # Create all tables
    python scripts/init_db.py seed        # Seed initial data
    python scripts/init_db.py reset       # Reset database (DROP + CREATE)
    python scripts/init_db.py show-schema # Display schema info
"""

import sys
import logging
from datetime import datetime
from app.core.database import engine, SessionLocal, create_all, drop_all
from app.core.config import settings
from app.models import (
    Base, User, Account, Post, Analytics, Trend, Hashtag, Asset,
    Schedule, Duplicate, Campaign, Log, UserPlan, SubscriptionStatus,
    Platform, PostStatus, ContentType
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_tables():
    """Create all database tables"""
    logger.info("Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Error creating tables: {e}")
        return False


def drop_tables():
    """Drop all database tables (DESTRUCTIVE)"""
    logger.warning("⚠️  This will DELETE all data from the database!")
    confirm = input("Type 'yes' to confirm: ")
    if confirm.lower() != 'yes':
        logger.info("Cancelled.")
        return False
    
    logger.info("Dropping all tables...")
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("✓ All tables dropped")
        return True
    except Exception as e:
        logger.error(f"✗ Error dropping tables: {e}")
        return False


def reset_database():
    """Reset database (DROP + CREATE)"""
    logger.warning("⚠️  This will DELETE all data and recreate the database!")
    confirm = input("Type 'yes' to confirm: ")
    if confirm.lower() != 'yes':
        logger.info("Cancelled.")
        return False
    
    if not drop_tables():
        return False
    
    return create_tables()


def seed_initial_data():
    """Seed initial test data"""
    logger.info("Seeding initial data...")
    db = SessionLocal()
    
    try:
        # Create test user
        test_user = User(
            email='demo@example.com',
            username='demo_user',
            password_hash='hashed_password_here',
            first_name='Demo',
            last_name='User',
            plan=UserPlan.PRO.value,
            subscription_status=SubscriptionStatus.ACTIVE.value,
            organization_name='Demo Organization',
            is_verified=True,
            is_active=True,
        )
        db.add(test_user)
        db.flush()
        logger.info(f"✓ Created test user: {test_user.email}")
        
        # Create test account
        test_account = Account(
            user_id=test_user.id,
            platform=Platform.INSTAGRAM.value,
            platform_user_id='12345678',
            username='demo_instagram',
            display_name='Demo Account',
            is_active=True,
            is_verified=True,
        )
        db.add(test_account)
        db.flush()
        logger.info(f"✓ Created test account: @{test_account.username}")
        
        # Create test post
        test_post = Post(
            user_id=test_user.id,
            account_id=test_account.id,
            title='Sample Post',
            script='This is a sample post script',
            caption='Check out this amazing content!',
            category='motivation',
            content_type=ContentType.REEL.value,
            status=PostStatus.DRAFT.value,
            quality_score=85.5,
            language='en',
        )
        db.add(test_post)
        db.flush()
        logger.info(f"✓ Created test post: {test_post.title}")
        
        # Create test trend
        test_trend = Trend(
            title='AI Content Creation',
            slug='ai-content-creation',
            trend_score=92.5,
            viral_score=88.3,
            source='google_trends',
            is_active=True,
            is_rising=True,
        )
        db.add(test_trend)
        db.flush()
        logger.info(f"✓ Created test trend: {test_trend.title}")
        
        # Create test hashtag
        test_hashtag = Hashtag(
            tag='ai_content',
            trending_score=85.0,
            is_trending=True,
            category='technology',
        )
        db.add(test_hashtag)
        db.flush()
        logger.info(f"✓ Created test hashtag: #{test_hashtag.tag}")
        
        # Create test campaign
        test_campaign = Campaign(
            user_id=test_user.id,
            name='Sample Campaign',
            slug='sample-campaign',
            objective='engagement',
            status='draft',
        )
        db.add(test_campaign)
        db.flush()
        logger.info(f"✓ Created test campaign: {test_campaign.name}")
        
        # Commit all changes
        db.commit()
        logger.info("✓ Initial data seeded successfully")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"✗ Error seeding data: {e}")
        return False
    finally:
        db.close()


def show_schema():
    """Display database schema information"""
    logger.info("Database Schema Information:")
    logger.info("=" * 60)
    
    from sqlalchemy import inspect
    inspector = inspect(engine)
    
    tables = inspector.get_table_names()
    logger.info(f"\nTotal Tables: {len(tables)}")
    logger.info("-" * 60)
    
    for table_name in tables:
        columns = inspector.get_columns(table_name)
        logger.info(f"\n📋 Table: {table_name}")
        logger.info(f"   Columns: {len(columns)}")
        for col in columns[:5]:  # Show first 5 columns
            logger.info(f"     - {col['name']}: {col['type']}")
        if len(columns) > 5:
            logger.info(f"     ... and {len(columns) - 5} more")
        
        indexes = inspector.get_indexes(table_name)
        if indexes:
            logger.info(f"   Indexes: {len(indexes)}")


def show_help():
    """Display help message"""
    help_text = """
    Database Initialization Script
    
    Usage: python scripts/init_db.py <command>
    
    Commands:
        create        Create all database tables
        seed          Seed initial test data
        reset         Reset database (DROP + CREATE) ⚠️  DESTRUCTIVE
        drop          Drop all tables ⚠️  DESTRUCTIVE
        show-schema   Display schema information
        help          Show this help message
    
    Examples:
        python scripts/init_db.py create
        python scripts/init_db.py seed
        python scripts/init_db.py reset
    
    Environment:
        Set DATABASE_URL in .env to customize database connection
        Current: {database_url}
    """.format(database_url=settings.database_url)
    
    print(help_text)


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        show_help()
        return 1
    
    command = sys.argv[1].lower()
    
    if command == 'create':
        success = create_tables()
    elif command == 'seed':
        if not create_tables():
            return 1
        success = seed_initial_data()
    elif command == 'reset':
        success = reset_database()
    elif command == 'drop':
        success = drop_tables()
    elif command == 'show-schema':
        show_schema()
        return 0
    elif command == 'help':
        show_help()
        return 0
    else:
        logger.error(f"Unknown command: {command}")
        show_help()
        return 1
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

