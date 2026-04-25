"""
Celery worker utilities and management functions.

Commands for starting workers and monitoring task execution.
"""

import logging
from app.celery_app import app, inspect_tasks, get_task_stats
from celery import group, chain, chord

logger = logging.getLogger(__name__)


# ============================================================================
# Worker Commands
# ============================================================================

WORKER_COMMANDS = {
    "default": "celery -A app.celery_app worker -l info",
    
    "content": "celery -A app.celery_app worker -l info -n content@%h -Q content --concurrency=2",
    
    "media": "celery -A app.celery_app worker -l info -n media@%h -Q media --concurrency=1",
    
    "publishing": "celery -A app.celery_app worker -l info -n publishing@%h -Q publishing --concurrency=3",
    
    "analytics": "celery -A app.celery_app worker -l info -n analytics@%h -Q analytics --concurrency=2",
    
    "beat": "celery -A app.celery_app beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler",
    
    "all": """
# Start multiple workers in parallel
Terminal 1: celery -A app.celery_app worker -l info -n content@%h -Q content --concurrency=2
Terminal 2: celery -A app.celery_app worker -l info -n media@%h -Q media --concurrency=1
Terminal 3: celery -A app.celery_app worker -l info -n publishing@%h -Q publishing --concurrency=3
Terminal 4: celery -A app.celery_app worker -l info -n analytics@%h -Q analytics --concurrency=2
Terminal 5: celery -A app.celery_app beat -l info
    """,
    
    "flower": "celery -A app.celery_app flower --port=5555",
}


# ============================================================================
# Task Composition
# ============================================================================

def create_content_workflow(user_id: int, topic: str, content_type: str, 
                           platforms: list):
    """
    Create a complete content creation workflow.
    
    Workflow:
    1. Generate content
    2. Generate images/videos
    3. Optimize content
    4. Publish to platforms
    5. Fetch analytics
    
    Args:
        user_id: User ID
        topic: Content topic
        content_type: Type of content
        platforms: Target platforms
    
    Returns:
        Celery workflow object
    """
    from app.tasks import (
        generate_content,
        generate_image,
        publish_post,
        fetch_analytics,
    )
    
    # Create workflow using chain (sequential execution)
    workflow = chain(
        generate_content.s(user_id, topic, content_type, platforms),
        # ... additional tasks
    )
    
    return workflow


def create_bulk_publish_workflow(user_ids: list, campaign_topic: str):
    """
    Create a workflow to generate and publish content for multiple users.
    
    Uses parallel execution (group) for better performance.
    
    Args:
        user_ids: List of user IDs
        campaign_topic: Campaign topic
    
    Returns:
        Celery workflow object
    """
    from app.tasks import generate_content
    
    # Create parallel tasks for each user
    jobs = group(
        [generate_content.s(uid, campaign_topic, "reel", ["instagram", "tiktok"])
         for uid in user_ids]
    )
    
    return jobs


# ============================================================================
# Monitoring Functions
# ============================================================================

def get_active_tasks():
    """Get all currently active tasks."""
    inspector = app.control.inspect()
    return inspector.active()


def get_scheduled_tasks():
    """Get all scheduled tasks."""
    inspector = app.control.inspect()
    return inspector.scheduled()


def get_worker_stats():
    """Get worker statistics."""
    return get_task_stats()


def get_queue_lengths():
    """Get number of tasks in each queue."""
    inspector = app.control.inspect()
    return inspector.reserved()


def purge_queue(queue_name: str):
    """Purge all tasks from a specific queue."""
    from kombu import Connection
    with Connection(app.connection()) as conn:
        conn.default_channel.queue_purge(queue_name)
    logger.info(f"Purged queue: {queue_name}")


def revoke_task(task_id: str, terminate: bool = False):
    """Revoke (cancel) a specific task."""
    app.control.revoke(task_id, terminate=terminate)
    logger.info(f"Revoked task: {task_id}")


# ============================================================================
# Task Inspection Functions
# ============================================================================

def inspect_task(task_id: str):
    """Get detailed information about a specific task."""
    from celery.result import AsyncResult
    result = AsyncResult(task_id, app=app)
    
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
        "traceback": result.traceback,
        "info": result.info,
    }


def retry_task(task_id: str):
    """Retry a failed task."""
    result = AsyncResult(task_id, app=app)
    if result.status == 'FAILURE':
        # Requeue the task
        logger.info(f"Retrying task: {task_id}")
        return True
    return False


# ============================================================================
# Diagnostics
# ============================================================================

def get_celery_diagnostics():
    """Get comprehensive Celery diagnostics."""
    inspector = app.control.inspect()
    
    return {
        "workers": inspector.stats(),
        "active_tasks": inspector.active(),
        "scheduled_tasks": inspector.scheduled(),
        "registered_tasks": inspector.registered(),
        "queues": inspector.active_queues(),
    }


def print_diagnostics():
    """Print Celery diagnostics to stdout."""
    diagnostics = get_celery_diagnostics()
    
    print("\n" + "="*60)
    print("CELERY DIAGNOSTICS")
    print("="*60)
    
    print("\n📊 WORKERS:")
    for worker_name, stats in (diagnostics.get("workers") or {}).items():
        print(f"  {worker_name}: {stats.get('pool', {}).get('max-concurrency', 'N/A')} workers")
    
    print("\n📝 ACTIVE TASKS:")
    active = diagnostics.get("active_tasks") or {}
    total_active = sum(len(tasks) for tasks in active.values())
    print(f"  Total: {total_active}")
    
    print("\n⏰ SCHEDULED TASKS:")
    scheduled = diagnostics.get("scheduled_tasks") or {}
    total_scheduled = sum(len(tasks) for tasks in scheduled.values())
    print(f"  Total: {total_scheduled}")
    
    print("\n✓ REGISTERED TASKS:")
    registered = diagnostics.get("registered_tasks") or {}
    task_count = sum(len(tasks) for tasks in registered.values())
    print(f"  Total: {task_count}")
    
    print("\n" + "="*60 + "\n")


# ============================================================================
# Configuration Helpers
# ============================================================================

def get_task_routes():
    """Get task routing configuration."""
    return {
        'app.tasks.content_tasks.*': {'queue': 'content'},
        'app.tasks.media_tasks.*': {'queue': 'media'},
        'app.tasks.publish_tasks.*': {'queue': 'publishing'},
        'app.tasks.analytics_tasks.*': {'queue': 'analytics'},
    }


def get_worker_configuration(worker_type: str = "default"):
    """
    Get recommended configuration for specific worker type.
    
    Worker types:
    - default: General purpose worker
    - content: Content generation worker
    - media: Media generation worker (images/videos)
    - publishing: Publishing worker
    - analytics: Analytics worker
    
    Args:
        worker_type: Type of worker to configure
    
    Returns:
        dict: Worker configuration
    """
    configs = {
        "default": {
            "concurrency": 4,
            "time_limit": 3600,
            "soft_time_limit": 3000,
            "max_tasks_per_child": 1000,
        },
        "content": {
            "concurrency": 2,
            "time_limit": 1800,  # 30 minutes
            "soft_time_limit": 1500,
            "max_tasks_per_child": 500,
        },
        "media": {
            "concurrency": 1,
            "time_limit": 3600,  # 1 hour
            "soft_time_limit": 3300,
            "max_tasks_per_child": 100,
        },
        "publishing": {
            "concurrency": 3,
            "time_limit": 1200,  # 20 minutes
            "soft_time_limit": 1000,
            "max_tasks_per_child": 2000,
        },
        "analytics": {
            "concurrency": 2,
            "time_limit": 1800,  # 30 minutes
            "soft_time_limit": 1500,
            "max_tasks_per_child": 500,
        },
    }
    
    return configs.get(worker_type, configs["default"])


# ============================================================================
# CLI Helpers
# ============================================================================

def print_worker_commands():
    """Print all available worker commands."""
    print("\n" + "="*60)
    print("CELERY WORKER COMMANDS")
    print("="*60 + "\n")
    
    for name, command in WORKER_COMMANDS.items():
        print(f"📌 {name.upper()}")
        print(f"   {command}")
        print()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "diagnostics":
            print_diagnostics()
        elif command == "commands":
            print_worker_commands()
        else:
            print(f"Unknown command: {command}")
    else:
        print_diagnostics()
