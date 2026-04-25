"""API v1 router with all endpoint modules."""

from fastapi import APIRouter

from app.api.v1 import (
    accounts,
    analytics,
    auth,
    content,
    engines,
    health,
    learning,
    media,
    publish,
    strategy,
)

router = APIRouter(prefix="/api/v1")

router.include_router(health.router)
router.include_router(auth.router)
router.include_router(content.router)
router.include_router(publish.router)
router.include_router(analytics.router)
router.include_router(engines.router)
router.include_router(accounts.router)
router.include_router(media.router)
router.include_router(learning.router)
router.include_router(strategy.router)

__all__ = ["router"]
