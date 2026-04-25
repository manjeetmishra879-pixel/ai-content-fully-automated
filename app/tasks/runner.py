"""
Celery task runner script for local development and testing.

This script provides CLI commands for managing Celery workers and tasks.
"""

import click
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Worker Management Commands
# ============================================================================

@click.group()
def cli():
    """Celery worker management CLI."""
    pass


@cli.command()
@click.option('--queue', default='content', help='Queue name (content, media, publishing, analytics)')
@click.option('--concurrency', default=2, help='Number of concurrent workers')
@click.option('--loglevel', default='info', help='Log level')
def worker(queue, concurrency, loglevel):
    """Start a Celery worker."""
    import subprocess
    import sys
    
    cmd = [
        sys.executable, '-m', 'celery',
        '-A', 'app.celery_app',
        'worker',
        f'--loglevel={loglevel}',
        f'--concurrency={concurrency}',
        f'-Q {queue}',
        '-n', f'{queue}@%h',
    ]
    
    logger.info(f"Starting {queue} worker with {concurrency} concurrency")
    subprocess.run(' '.join(cmd), shell=True)


@cli.command()
@click.option('--scheduler', default='beat', help='Scheduler type')
def beat(scheduler):
    """Start Celery Beat scheduler."""
    import subprocess
    import sys
    
    cmd = [
        sys.executable, '-m', 'celery',
        '-A', 'app.celery_app',
        'beat',
        '--loglevel=info',
    ]
    
    logger.info("Starting Celery Beat scheduler")
    subprocess.run(' '.join(cmd), shell=True)


@cli.command()
@click.option('--port', default=5555, help='Flower port')
def flower(port):
    """Start Flower monitoring dashboard."""
    import subprocess
    import sys
    
    cmd = [
        sys.executable, '-m', 'celery',
        '-A', 'app.celery_app',
        'flower',
        f'--port={port}',
    ]
    
    logger.info(f"Starting Flower on port {port}")
    logger.info(f"Access at: http://localhost:{port}")
    subprocess.run(' '.join(cmd), shell=True)


# ============================================================================
# Task Management Commands
# ============================================================================

@cli.group()
def task():
    """Task management commands."""
    pass


@task.command()
@click.argument('user_id', type=int)
@click.argument('topic')
@click.argument('content_type')
@click.option('--platforms', default='instagram,tiktok', help='Comma-separated platforms')
def generate_content(user_id, topic, content_type, platforms):
    """Generate content."""
    from app.tasks import generate_content as gc_task
    
    platform_list = [p.strip() for p in platforms.split(',')]
    result = gc_task.delay(user_id, topic, content_type, platform_list)
    
    click.echo(f"✓ Task started: {result.id}")
    click.echo(f"  Topic: {topic}")
    click.echo(f"  Platforms: {platform_list}")


@task.command()
@click.argument('post_id', type=int)
@click.option('--platforms', default='instagram,tiktok', help='Comma-separated platforms')
def publish_post(post_id, platforms):
    """Publish a post."""
    from app.tasks import publish_post as pp_task
    
    platform_list = [p.strip() for p in platforms.split(',')]
    result = pp_task.delay(post_id, platform_list)
    
    click.echo(f"✓ Publish task started: {result.id}")
    click.echo(f"  Post ID: {post_id}")
    click.echo(f"  Platforms: {platform_list}")


@task.command()
@click.argument('post_id', type=int)
def fetch_analytics(post_id):
    """Fetch analytics for a post."""
    from app.tasks import fetch_analytics as fa_task
    
    result = fa_task.delay(post_id=post_id)
    
    click.echo(f"✓ Analytics task started: {result.id}")
    click.echo(f"  Post ID: {post_id}")


@task.command()
@click.argument('task_id')
def inspect(task_id):
    """Inspect task status and results."""
    from celery.result import AsyncResult
    from app.celery_app import app
    
    result = AsyncResult(task_id, app=app)
    
    click.echo(f"\n📊 Task: {task_id}")
    click.echo(f"   Status: {result.status}")
    
    if result.ready():
        if result.successful():
            click.echo(f"   Result: {result.result}")
        else:
            click.echo(f"   Error: {result.info}")
    else:
        click.echo(f"   Progress: {result.info}")


# ============================================================================
# Monitoring Commands
# ============================================================================

@cli.group()
def monitor():
    """Monitoring commands."""
    pass


@monitor.command()
def status():
    """Show Celery status."""
    from app.tasks.worker_utils import get_celery_diagnostics
    
    diag = get_celery_diagnostics()
    
    click.echo("\n📊 CELERY STATUS\n")
    
    workers = diag.get("workers") or {}
    click.echo(f"✓ Workers: {len(workers)}")
    for name in workers:
        click.echo(f"  - {name}")
    
    active = diag.get("active_tasks") or {}
    total_active = sum(len(tasks) for tasks in active.values())
    click.echo(f"\n✓ Active Tasks: {total_active}")
    
    scheduled = diag.get("scheduled_tasks") or {}
    total_scheduled = sum(len(tasks) for tasks in scheduled.values())
    click.echo(f"✓ Scheduled Tasks: {total_scheduled}")


@monitor.command()
def queues():
    """Show queue information."""
    from app.tasks.broker_utils import get_queue_info, get_queue_lengths
    
    queue_info = get_queue_info()
    queue_lengths = get_queue_lengths()
    
    click.echo("\n📋 QUEUE STATUS\n")
    
    for queue_name, info in queue_info.items():
        length = queue_lengths.get(queue_name, 0)
        workers = len(info.get("workers", []))
        click.echo(f"✓ {queue_name}")
        click.echo(f"  Tasks: {length}")
        click.echo(f"  Workers: {workers}")


@monitor.command()
def health():
    """Check system health."""
    from app.tasks.broker_utils import verify_celery_setup
    
    setup = verify_celery_setup()
    
    click.echo("\n🏥 SYSTEM HEALTH CHECK\n")
    
    status = setup.get("overall")
    color = "green" if status == "healthy" else "red"
    click.echo(f"Overall: {click.style(status.upper(), fg=color)}")
    
    checks = setup.get("checks", {})
    for check_name, check_result in checks.items():
        if "status" in check_result:
            status = check_result.get("status")
            color = "green" if status == "connected" else "red"
            click.echo(f"\n{check_name}:")
            click.echo(f"  Status: {click.style(status, fg=color)}")


# ============================================================================
# Development Commands
# ============================================================================

@cli.group()
def dev():
    """Development commands."""
    pass


@dev.command()
def purge():
    """Purge all tasks from queues."""
    from app.celery_app import app
    from kombu import Connection
    
    click.echo("⚠️  Purging all tasks from queues...")
    
    queues = ['content', 'media', 'publishing', 'analytics']
    
    with Connection(app.connection()) as conn:
        for queue in queues:
            try:
                conn.default_channel.queue_purge(queue)
                click.echo(f"✓ Purged: {queue}")
            except:
                click.echo(f"✗ Failed to purge: {queue}")


@dev.command()
def test():
    """Test Celery setup."""
    from app.celery_app import debug_task
    
    click.echo("Testing Celery setup...")
    result = debug_task.delay()
    
    click.echo(f"✓ Task submitted: {result.id}")
    click.echo("Wait for task to complete...")
    
    try:
        result.get(timeout=10)
        click.echo("✓ Celery is working correctly!")
    except Exception as e:
        click.echo(f"✗ Error: {e}")


# ============================================================================
# Usage Information
# ============================================================================

@cli.command()
def help_info():
    """Show help information."""
    help_text = """
    
═══════════════════════════════════════════════════════════════════════════
  CELERY TASK RUNNER - Help Information
═══════════════════════════════════════════════════════════════════════════

WORKERS:
  python -m app.tasks.runner worker --queue content --concurrency 2
  python -m app.tasks.runner worker --queue media --concurrency 1
  python -m app.tasks.runner worker --queue publishing --concurrency 3
  python -m app.tasks.runner beat             (Start task scheduler)
  python -m app.tasks.runner flower           (Start monitoring)

TASKS:
  python -m app.tasks.runner task generate-content <user_id> <topic> <type>
  python -m app.tasks.runner task publish-post <post_id>
  python -m app.tasks.runner task fetch-analytics <post_id>
  python -m app.tasks.runner task inspect <task_id>

MONITORING:
  python -m app.tasks.runner monitor status   (Show status)
  python -m app.tasks.runner monitor queues   (Show queues)
  python -m app.tasks.runner monitor health   (Health check)

DEVELOPMENT:
  python -m app.tasks.runner dev test         (Test setup)
  python -m app.tasks.runner dev purge        (Purge tasks)

═══════════════════════════════════════════════════════════════════════════
    """
    click.echo(help_text)


if __name__ == '__main__':
    cli()
