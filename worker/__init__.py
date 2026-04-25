"""
Celery worker package for async task processing
"""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "content_platform",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "worker.tasks.content_tasks",
        "worker.tasks.publishing_tasks",
        "worker.tasks.analytics_tasks",
        "worker.tasks.trend_tasks",
    ]
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)
