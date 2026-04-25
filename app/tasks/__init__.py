"""
Celery tasks package.

Organizes all async tasks for content generation, publishing, analytics, etc.
"""

from app.tasks import (
    content_tasks,
    media_tasks,
    publish_tasks,
    analytics_tasks,
)

# Import all tasks for auto-discovery
from app.tasks.content_tasks import (
    generate_content,
    generate_batch_content,
    optimize_content,
)

from app.tasks.media_tasks import (
    generate_image,
    generate_video,
    edit_video,
)

from app.tasks.publish_tasks import (
    publish_post,
    publish_scheduled_post,
    publish_bulk,
    retry_failed_publishes,
)

from app.tasks.analytics_tasks import (
    fetch_analytics,
    aggregate_daily_analytics,
    fetch_trending_topics,
    cleanup_old_results,
    calculate_insights,
)

__all__ = [
    # Content tasks
    "generate_content",
    "generate_batch_content",
    "optimize_content",
    # Media tasks
    "generate_image",
    "generate_video",
    "edit_video",
    # Publishing tasks
    "publish_post",
    "publish_scheduled_post",
    "publish_bulk",
    "retry_failed_publishes",
    # Analytics tasks
    "fetch_analytics",
    "aggregate_daily_analytics",
    "fetch_trending_topics",
    "cleanup_old_results",
    "calculate_insights",
]
