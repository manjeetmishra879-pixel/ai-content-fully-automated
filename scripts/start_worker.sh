#!/bin/bash
# Start Celery worker

set -e

echo "Starting Celery worker..."

celery -A worker worker \
    --loglevel=info \
    --concurrency=4 \
    --max-tasks-per-child=100 \
    --without-gossip \
    --without-mingle \
    --without-heartbeat

echo "Worker started"
