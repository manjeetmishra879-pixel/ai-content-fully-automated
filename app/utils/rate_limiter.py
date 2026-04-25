"""
Rate limiting utilities for platform API calls.

Handles rate limits, quota management, and exponential backoff.
"""

import time
import logging
from functools import wraps
from typing import Dict, Any, Optional
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter using Redis for distributed rate limiting."""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client or redis.Redis.from_url(settings.REDIS_URL)

    def is_allowed(self, key: str, max_calls: int, window_seconds: int) -> bool:
        """
        Check if a request is allowed under rate limit.

        Args:
            key: Unique identifier for the rate limit (e.g., "instagram_api_user_123")
            max_calls: Maximum calls allowed in the window
            window_seconds: Time window in seconds

        Returns:
            bool: True if allowed, False if rate limited
        """
        try:
            current_time = int(time.time())
            window_start = current_time - window_seconds

            # Clean old entries and count current ones
            self.redis.zremrangebyscore(key, 0, window_start)
            current_count = self.redis.zcard(key)

            if current_count >= max_calls:
                return False

            # Add current request
            self.redis.zadd(key, {str(current_time): current_time})
            self.redis.expire(key, window_seconds)

            return True

        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            return True  # Allow on error to avoid blocking functionality


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(max_calls: int, period_seconds: int, platform: str = "unknown"):
    """
    Decorator for rate limiting API calls.

    Args:
        max_calls: Maximum calls allowed in the period
        period_seconds: Time period in seconds
        platform: Platform name for logging

    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a unique key based on function name and user/platform
            user_id = kwargs.get('user_id', 'unknown')
            key = f"ratelimit:{platform}:{func.__name__}:{user_id}"

            if not rate_limiter.is_allowed(key, max_calls, period_seconds):
                logger.warning(f"Rate limit exceeded for {platform} API call: {func.__name__}")
                raise RateLimitExceededError(
                    f"Rate limit exceeded for {platform}. Max {max_calls} calls per {period_seconds}s"
                )

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                # Log API errors for monitoring
                logger.error(f"API call failed for {platform}.{func.__name__}: {e}")
                raise

        return wrapper
    return decorator


class RateLimitExceededError(Exception):
    """Exception raised when rate limit is exceeded."""
    pass


def exponential_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 300.0) -> float:
    """
    Calculate exponential backoff delay.

    Args:
        attempt: Current attempt number (0-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Delay in seconds
    """
    delay = base_delay * (2 ** attempt)
    return min(delay, max_delay)


# Platform-specific rate limits (conservative defaults)
PLATFORM_RATE_LIMITS = {
    "instagram": {"calls": 200, "period": 3600},  # 200 calls per hour
    "tiktok": {"calls": 100, "period": 3600},    # 100 calls per hour
    "youtube": {"calls": 10000, "period": 86400}, # 10,000 units per day
    "facebook": {"calls": 200, "period": 3600},  # 200 calls per hour
    "twitter": {"calls": 300, "period": 900},   # 300 calls per 15 minutes
    "linkedin": {"calls": 100, "period": 3600}, # 100 calls per hour
}


def get_platform_rate_limit(platform: str) -> Dict[str, int]:
    """
    Get rate limit configuration for a platform.

    Args:
        platform: Platform name

    Returns:
        Dict with 'calls' and 'period' keys
    """
    return PLATFORM_RATE_LIMITS.get(platform.lower(), {"calls": 100, "period": 3600})


def create_rate_limited_api_call(platform: str):
    """
    Create a rate-limited decorator for a specific platform.

    Args:
        platform: Platform name

    Returns:
        Rate limiting decorator
    """
    limits = get_platform_rate_limit(platform)
    return rate_limit(limits["calls"], limits["period"], platform)