"""
API v1 health check endpoints.
"""

from fastapi import APIRouter, Depends
from datetime import datetime
from sqlalchemy import text
from app.schemas import HealthResponse
from app.core.database import SessionLocal

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    
    Returns service status and component health checks.
    """
    # Check database connection
    db_status = "connected"
    cache_status = "connected"
    
    try:
        db = SessionLocal()
        # Simple query to test connection
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        db_status = f"disconnected: {str(e)}"
    
    try:
        # Check Redis/cache connection
        # TODO: Implement Redis health check when cache is configured
        pass
    except Exception as e:
        cache_status = f"disconnected: {str(e)}"
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow(),
        database=db_status,
        cache=cache_status
    )


@router.get("/ready")
async def readiness_check():
    """
    Readiness check - indicates if service is ready to accept requests.
    """
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return {"ready": True, "timestamp": datetime.utcnow()}
    except Exception as e:
        return {"ready": False, "error": str(e)}, 503


@router.get("/live")
async def liveness_check():
    """
    Liveness check - indicates if service is running.
    """
    return {"alive": True, "timestamp": datetime.utcnow()}
