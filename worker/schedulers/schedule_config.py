"""
Celery Beat schedule configuration for periodic tasks
"""

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Trend monitoring
    'fetch-trends-every-30m': {
        'task': 'fetch_trends',
        'schedule': 30 * 60,  # Every 30 minutes
    },
    'detect-viral-trends-every-15m': {
        'task': 'detect_viral_trends',
        'schedule': 15 * 60,  # Every 15 minutes
    },
    'analyze-competitors-daily': {
        'task': 'analyze_competitors',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM UTC
    },
    
    # Analytics tracking
    'fetch-analytics-hourly': {
        'task': 'fetch_analytics',
        'schedule': 60 * 60,  # Every hour
    },
    'aggregate-metrics-daily': {
        'task': 'aggregate_metrics',
        'schedule': crontab(hour=1, minute=0),  # Daily at 1 AM UTC
    },
    'detect-shadowban-daily': {
        'task': 'detect_shadowban',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM UTC
    },
    'learn-optimal-times-weekly': {
        'task': 'learn_optimal_times',
        'schedule': crontab(day_of_week=1, hour=0, minute=0),  # Weekly on Monday
    },
    
    # Publishing & Account management
    'sync-social-accounts-every-2h': {
        'task': 'sync_social_accounts',
        'schedule': 2 * 60 * 60,  # Every 2 hours
    },
    'rotate-accounts-daily': {
        'task': 'rotate_accounts',
        'schedule': crontab(hour=6, minute=0),  # Daily at 6 AM UTC
    },
}
