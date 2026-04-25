"""
FastAPI Application Entry Point.

Main FastAPI application with:
- API versioning (v1)
- CORS middleware
- Exception handling
- Logging
- Health checks
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
import logging
from datetime import datetime

from app.core.config import settings
from app.api import v1_router
from app.core.database import create_all, SessionLocal

# ============================================================================
# Setup Logging
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Lifespan Events
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle startup and shutdown events.
    
    Startup: Ensure database tables exist
    Shutdown: Clean up resources
    """
    # Startup
    logger.info("Starting up AI Content Platform...")
    try:
        create_all()
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    # Seed a default user (id=1) for single-tenant dev mode.
    try:
        from app.models.models import User, UserPlan
        db = SessionLocal()
        try:
            if not db.query(User).filter(User.id == 1).first():
                user = User(
                    id=1,
                    email="default@local",
                    username="default",
                    password_hash="!",
                    plan=UserPlan.FREE,
                    is_active=True,
                )
                db.add(user)
                db.commit()
                logger.info("Seeded default user id=1")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to seed default user: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Content Platform...")


# ============================================================================
# Create FastAPI Application
# ============================================================================

app = FastAPI(
    title="AI Content Platform API",
    description="Automated AI-powered content generation and publishing platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)


# ============================================================================
# CORS Middleware
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Logging Middleware
# ============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests and responses."""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    return response


# ============================================================================
# Custom OpenAPI Schema
# ============================================================================

def custom_openapi():
    """Customize OpenAPI schema with API versioning info."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="AI Content Platform API",
        version="1.0.0",
        description="""
        ## Overview
        
        Automated AI-powered content generation and publishing platform for social media.
        
        ### Key Features
        - **AI Content Generation**: Generate optimized content using AI
        - **Multi-Platform Publishing**: Publish to Instagram, TikTok, YouTube, and more
        - **Analytics & Insights**: Track performance and get AI-powered recommendations
        - **Trend Detection**: Discover and leverage trending topics
        - **Campaign Management**: Organize and track marketing campaigns
        
        ### API Versioning
        - Currently on **v1** of the API
        - All endpoints follow `/api/v1/{resource}` pattern
        
        ### Authentication
        - Use `/api/v1/auth/register` to create account
        - Use `/api/v1/auth/login` to get access token
        - Include token in `Authorization: Bearer <token>` header for protected endpoints
        
        ### Rate Limiting
        - Free plan: 100 requests/hour
        - Pro plan: 1000 requests/hour
        - Enterprise: Unlimited
        """,
        routes=app.routes,
        tags=[
            {"name": "health", "description": "Service health and readiness checks"},
            {"name": "authentication", "description": "User registration, login, and token management"},
            {"name": "content", "description": "AI content generation and trend discovery"},
            {"name": "publishing", "description": "Content publishing and scheduling"},
            {"name": "analytics", "description": "Performance metrics and AI insights"},
        ]
    )
    
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# ============================================================================
# Include API Routers
# ============================================================================

app.include_router(v1_router)


# ============================================================================
# Root Endpoints
# ============================================================================

@app.get("/")
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "name": "AI Content Platform API",
        "version": "1.0.0",
        "status": "active",
        "documentation": "/api/docs",
        "api_v1_base": "/api/v1",
        "endpoints": {
            "health": "/api/v1/health",
            "auth": "/api/v1/auth",
            "content": "/api/v1/content",
            "publish": "/api/v1/publish",
            "analytics": "/api/v1/analytics"
        }
    }


@app.get("/status")
async def status():
    """
    Get current API status.
    """
    return {
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }


# ============================================================================
# API Versioning Info
# ============================================================================

@app.get("/api")
async def api_info():
    """
    Get API versioning information.
    """
    return {
        "current_version": "v1",
        "versions": {
            "v1": {
                "status": "stable",
                "base_url": "/api/v1",
                "endpoints": {
                    "health": "/api/v1/health",
                    "auth": "/api/v1/auth",
                    "content": "/api/v1/content",
                    "publish": "/api/v1/publish",
                    "analytics": "/api/v1/analytics"
                },
                "features": [
                    "User authentication with JWT",
                    "AI-powered content generation",
                    "Multi-platform content publishing",
                    "Advanced analytics and insights",
                    "Trend discovery and recommendations",
                    "Campaign management"
                ]
            }
        },
        "documentation": {
            "swagger_ui": "/api/docs",
            "redoc": "/api/redoc",
            "openapi_schema": "/api/openapi.json"
        }
    }


# ============================================================================
# Startup/Shutdown Events (Alternative Event Handlers)
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger.info("=" * 60)
    logger.info("AI Content Platform API is starting up")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info("=" * 60)
    logger.info("AI Content Platform API is shutting down")
    logger.info("=" * 60)


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting AI Content Platform API server...")
    
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
