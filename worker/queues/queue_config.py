"""
Queue routing and configuration
"""

from celery import Queue, Exchange

# Queue definitions
QUEUES = {
    'high_priority': Queue('high_priority', Exchange('high_priority'), routing_key='high_priority'),
    'content_generation': Queue('content_generation', Exchange('content'), routing_key='content.*'),
    'publishing': Queue('publishing', Exchange('publishing'), routing_key='publishing.*'),
    'analytics': Queue('analytics', Exchange('analytics'), routing_key='analytics.*'),
    'trends': Queue('trends', Exchange('trends'), routing_key='trends.*'),
    'low_priority': Queue('low_priority', Exchange('low_priority'), routing_key='low_priority'),
    'dead_letter': Queue('dead_letter', Exchange('dead_letter'), routing_key='dead_letter'),
}

# Task routing
TASK_ROUTES = {
    'generate_content': {'queue': 'high_priority', 'routing_key': 'high_priority'},
    'generate_video': {'queue': 'content_generation', 'routing_key': 'content.video'},
    'publish_content': {'queue': 'high_priority', 'routing_key': 'high_priority'},
    'fetch_analytics': {'queue': 'analytics', 'routing_key': 'analytics.fetch'},
    'fetch_trends': {'queue': 'trends', 'routing_key': 'trends.fetch'},
}
