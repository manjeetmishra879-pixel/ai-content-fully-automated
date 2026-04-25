"""
Celery application factory and configuration.

Initializes Celery with Redis broker for async task processing.
Includes task routing, scheduling, and result backend configuration.
"""

from celery import Celery
from celery.schedules import crontab
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# Create Celery App Instance
# ============================================================================

app = Celery(
    'ai_content_platform',
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# ============================================================================
# Celery Configuration
# ============================================================================

app.conf.update(
    # Task Configuration
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task Execution
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    
    # Worker Configuration
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Result Backend
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        'master_name': 'mymaster',
        'retry_on_timeout': True,
        'socket_connect_timeout': 5,
        'socket_timeout': 5,
        'retry': True,
        'retry_on_timeout': True,
    },
    
    # Broker Configuration
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    broker_transport_options={
        'master_name': 'mymaster',
        'retry_on_timeout': True,
        'socket_connect_timeout': 5,
        'socket_timeout': 5,
        'retry': True,
        'retry_on_timeout': True,
    },
    
    # Task Routing
    task_routes={
        'app.tasks.content_tasks.*': {'queue': 'content'},
        'app.tasks.media_tasks.*': {'queue': 'media'},
        'app.tasks.publish_tasks.*': {'queue': 'publishing'},
        'app.tasks.analytics_tasks.*': {'queue': 'analytics'},
    },
    
    # Task Priority
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Periodic Tasks (Beat Schedule)
    beat_schedule={
        'fetch-trending-every-hour': {
            'task': 'app.tasks.analytics_tasks.fetch_trending_topics',
            'schedule': crontab(minute=0),  # Every hour
            'args': (),
        },
        'aggregate-analytics-every-6-hours': {
            'task': 'app.tasks.analytics_tasks.aggregate_daily_analytics',
            'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
            'args': (),
        },
        'cleanup-old-tasks-daily': {
            'task': 'app.tasks.analytics_tasks.cleanup_old_results',
            'schedule': crontab(hour=2, minute=0),  # 2 AM UTC daily
            'args': (),
        },
    },
)

# ============================================================================
# Task Auto-discovery
# ============================================================================

app.autodiscover_tasks(['app.tasks'])


# ============================================================================
# Celery Event Handlers
# ============================================================================

@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f'Request: {self.request!r}')
    logger.info(f"Debug task executed: {self.request}")


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks after Celery is configured."""
    logger.info("Celery periodic tasks configured")


@app.task(bind=True)
def on_failure(self, exc, task_id, args, kwargs, einfo):
    """Handle task failures."""
    logger.error(f"Task {task_id} failed: {exc}")


# ============================================================================
# Helper Functions
# ============================================================================

def get_celery_app():
    """Get the Celery app instance."""
    return app


def inspect_tasks():
    """Get information about active tasks."""
    inspector = app.control.inspect()
    return {
        'active': inspector.active(),
        'scheduled': inspector.scheduled(),
        'reserved': inspector.reserved(),
        'stats': inspector.stats(),
    }


def get_task_stats():
    """Get task statistics."""
    inspector = app.control.inspect()
    stats = inspector.stats()
    
    if not stats:
        return {}
    
    return {
        'workers': list(stats.keys()),
        'total_workers': len(stats),
        'worker_stats': stats,
    }
