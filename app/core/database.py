"""
Database connection and session management
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.models import Base

# Create database engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_pre_ping=True,  # Verify connections before using
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def get_db() -> Session:
    """
    Dependency for getting database session.
    Use in FastAPI routes:
        async def my_route(db: Session = Depends(get_db)):
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all():
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)


def drop_all():
    """Drop all tables from the database (USE WITH CAUTION)"""
    Base.metadata.drop_all(bind=engine)


def init_db():
    """Initialize the database"""
    create_all()

