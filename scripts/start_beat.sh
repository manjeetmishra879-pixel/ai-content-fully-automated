#!/bin/bash
# Start Celery Beat scheduler

set -e

echo "Starting Celery Beat..."

celery -A worker beat \
    --loglevel=info \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler

echo "Beat scheduler started"
