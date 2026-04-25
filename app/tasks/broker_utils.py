"""
Celery and Redis setup for development environment.

This module provides utilities for:
- Redis connection management
- Celery worker initialization
- Task monitoring and management
"""

import logging
from redis import Redis
from app.core.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Redis Connection
# ============================================================================

def get_redis_connection():
    """Get Redis connection instance."""
    try:
        redis_client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            socket_keepalive=True,
            socket_keepalive_options={
                1: 1,  # TCP_KEEPIDLE
                2: 3,  # TCP_KEEPINTVL
                3: 5,  # TCP_KEEPCNT
            }
        )
        # Test connection
        redis_client.ping()
        logger.info("Redis connection established")
        return redis_client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise


# ============================================================================
# Celery Broker Status
# ============================================================================

def check_broker_status():
    """Check if Celery broker is accessible."""
    try:
        redis_client = get_redis_connection()
        info = redis_client.info()
        return {
            "status": "connected",
            "redis_version": info.get("redis_version"),
            "memory_used": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
        }
    except Exception as e:
        return {
            "status": "disconnected",
            "error": str(e),
        }


def get_broker_stats():
    """Get broker (Redis) statistics."""
    try:
        redis_client = get_redis_connection()
        return {
            "memory": redis_client.info("memory"),
            "stats": redis_client.info("stats"),
            "replication": redis_client.info("replication"),
        }
    except Exception as e:
        logger.error(f"Failed to get broker stats: {e}")
        return None


# ============================================================================
# Celery Setup Verification
# ============================================================================

def verify_celery_setup():
    """Verify complete Celery setup."""
    from app.celery_app import app
    
    checks = {
        "broker": check_broker_status(),
        "backend": check_result_backend(),
        "workers_registered": check_registered_workers(),
        "tasks_registered": check_registered_tasks(),
    }
    
    all_healthy = all(
        check.get("status") == "connected" or check.get("healthy")
        for check in checks.values()
    )
    
    return {
        "overall": "healthy" if all_healthy else "unhealthy",
        "checks": checks,
    }


def check_result_backend():
    """Check if result backend is accessible."""
    try:
        redis_client = get_redis_connection()
        redis_client.set("celery_test", "test", ex=60)
        return {"status": "connected"}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)}


def check_registered_workers():
    """Check registered workers."""
    from app.celery_app import app
    inspector = app.control.inspect()
    stats = inspector.stats()
    if stats:
        return {
            "healthy": True,
            "count": len(stats),
            "workers": list(stats.keys()),
        }
    return {"healthy": False, "count": 0, "workers": []}


def check_registered_tasks():
    """Check registered tasks."""
    from app.celery_app import app
    inspector = app.control.inspect()
    tasks = inspector.registered()
    if tasks:
        total_tasks = sum(len(t) for t in tasks.values())
        return {"healthy": True, "count": total_tasks}
    return {"healthy": False, "count": 0}


# ============================================================================
# Queue Management
# ============================================================================

def get_queue_info():
    """Get information about all queues."""
    from app.celery_app import app
    inspector = app.control.inspect()
    queues = inspector.active_queues()
    
    queue_info = {}
    for worker_name, worker_queues in (queues or {}).items():
        for queue in worker_queues:
            queue_name = queue.get("name")
            if queue_name not in queue_info:
                queue_info[queue_name] = {
                    "name": queue_name,
                    "workers": [],
                }
            queue_info[queue_name]["workers"].append(worker_name)
    
    return queue_info


def get_queue_lengths():
    """Get number of tasks in each queue."""
    try:
        redis_client = get_redis_connection()
        
        queues = {
            "content": redis_client.llen("celery:content"),
            "media": redis_client.llen("celery:media"),
            "publishing": redis_client.llen("celery:publishing"),
            "analytics": redis_client.llen("celery:analytics"),
        }
        
        return queues
    except Exception as e:
        logger.error(f"Failed to get queue lengths: {e}")
        return {}


# ============================================================================
# Cache Operations
# ============================================================================

def clear_cache():
    """Clear all cache data."""
    try:
        redis_client = get_redis_connection()
        redis_client.flushdb()
        logger.info("Cache cleared successfully")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        return {"status": "failed", "error": str(e)}


def get_cache_size():
    """Get total cache size."""
    try:
        redis_client = get_redis_connection()
        info = redis_client.info("memory")
        return {
            "memory_used": info.get("used_memory_human"),
            "memory_peak": info.get("used_memory_peak_human"),
            "memory_limit": info.get("maxmemory_human"),
        }
    except Exception as e:
        logger.error(f"Failed to get cache size: {e}")
        return None


# ============================================================================
# Health Checks for Docker
# ============================================================================

def healthcheck_redis():
    """Health check for Redis (for Docker HEALTHCHECK)."""
    try:
        redis_client = get_redis_connection()
        redis_client.ping()
        return 0  # Success
    except:
        return 1  # Failure


def healthcheck_celery():
    """Health check for Celery workers (for Docker HEALTHCHECK)."""
    try:
        from app.celery_app import app
        inspector = app.control.inspect()
        stats = inspector.stats()
        if stats and len(stats) > 0:
            return 0  # Success
        return 1  # No workers
    except:
        return 1  # Failure
