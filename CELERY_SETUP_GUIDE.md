# Celery Worker Setup - Complete Guide

## Overview

This document provides comprehensive guidance on setting up and using Celery for async task processing in the AI Content Platform.

---

## 📦 Architecture

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                       │
│  (HTTP Requests → Task Queue)                                   │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
        ┌─────────────────┐
        │  Redis Broker   │  (Message Queue)
        │  (localhost:    │
        │   6379)         │
        └────────┬────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
    ┌────────────┐  ┌────────────┐
    │  Worker 1  │  │  Worker 2  │  (Process Tasks)
    │ (Content)  │  │  (Media)   │
    └────────────┘  └────────────┘
        │                 │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  PostgreSQL DB  │  (Store Results)
        └─────────────────┘
```

### Task Queues

| Queue | Purpose | Concurrency | Tasks |
|-------|---------|-------------|-------|
| **content** | Content generation | 2 | generate_content, generate_batch_content, optimize_content |
| **media** | Image/video generation | 1 | generate_image, generate_video, edit_video |
| **publishing** | Post publishing | 3 | publish_post, publish_scheduled_post, publish_bulk |
| **analytics** | Analytics collection | 2 | fetch_analytics, aggregate_daily_analytics, fetch_trending_topics |

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install celery[redis] redis click pydantic
```

### 2. Start Redis

```bash
# Using Docker
docker run -d -p 6379:6379 redis:latest

# Or using Homebrew (macOS)
brew services start redis

# Or using apt (Linux)
sudo apt-get install redis-server
sudo systemctl start redis-server
```

### 3. Start Workers

**Terminal 1 - Content Worker:**
```bash
celery -A app.celery_app worker -l info -n content@%h -Q content --concurrency=2
```

**Terminal 2 - Media Worker:**
```bash
celery -A app.celery_app worker -l info -n media@%h -Q media --concurrency=1
```

**Terminal 3 - Publishing Worker:**
```bash
celery -A app.celery_app worker -l info -n publishing@%h -Q publishing --concurrency=3
```

**Terminal 4 - Analytics Worker:**
```bash
celery -A app.celery_app worker -l info -n analytics@%h -Q analytics --concurrency=2
```

**Terminal 5 - Beat Scheduler:**
```bash
celery -A app.celery_app beat -l info
```

**Terminal 6 - Flower Monitoring:**
```bash
celery -A app.celery_app flower --port=5555
```

### 4. Access Monitoring Dashboard

Open browser to: `http://localhost:5555`

---

## 📝 Task Reference

### Content Tasks

#### 1. Generate Content
```python
from app.tasks import generate_content

result = generate_content.delay(
    user_id=1,
    topic="AI and Machine Learning",
    content_type="reel",
    platforms=["instagram", "tiktok"],
    tone="professional",
    language="english"
)

print(result.id)  # Task ID
print(result.get())  # Wait for result
```

#### 2. Generate Batch Content
```python
from app.tasks import generate_batch_content

result = generate_batch_content.delay(
    user_id=1,
    topics=["AI", "Blockchain", "Cloud Computing"],
    content_type="short",
    platforms=["tiktok", "youtube"],
)
```

#### 3. Optimize Content
```python
from app.tasks import optimize_content

result = optimize_content.delay(
    post_id=5,
    optimization_type="engagement"  # seo, engagement, viral, accessibility
)
```

### Media Tasks

#### 1. Generate Image
```python
from app.tasks import generate_image

result = generate_image.delay(
    user_id=1,
    post_id=5,
    prompt="A futuristic AI robot",
    style="modern",
    resolution="1080x1080"
)
```

#### 2. Generate Video
```python
from app.tasks import generate_video

result = generate_video.delay(
    user_id=1,
    post_id=5,
    script="Welcome to the future of content creation...",
    video_type="short_form",
    duration=30,
    music=True,
    subtitles=True
)
```

#### 3. Edit Video
```python
from app.tasks import edit_video

result = edit_video.delay(
    asset_id=10,
    edits={
        "trim": {"start": 2, "end": 28},
        "speed": 1.2,
        "filter": "noir"
    }
)
```

### Publishing Tasks

#### 1. Publish Post
```python
from app.tasks import publish_post

result = publish_post.delay(
    post_id=5,
    platforms=["instagram", "tiktok", "youtube"],
    notify=True
)
```

#### 2. Publish Scheduled Post
```python
from app.tasks import publish_scheduled_post

result = publish_scheduled_post.delay(schedule_id=15)
```

#### 3. Bulk Publish
```python
from app.tasks import publish_bulk

result = publish_bulk.delay(
    post_ids=[1, 2, 3, 4, 5],
    platforms=["instagram", "tiktok"]
)
```

### Analytics Tasks

#### 1. Fetch Analytics
```python
from app.tasks import fetch_analytics

# For specific post
result = fetch_analytics.delay(post_id=5)

# For entire account
result = fetch_analytics.delay(account_id=10)
```

#### 2. Aggregate Daily Analytics
```python
from app.tasks import aggregate_daily_analytics

result = aggregate_daily_analytics.delay()
```

#### 3. Fetch Trending Topics
```python
from app.tasks import fetch_trending_topics

result = fetch_trending_topics.delay()
```

#### 4. Calculate Insights
```python
from app.tasks import calculate_insights

result = calculate_insights.delay(
    account_id=10,
    period="week"  # week, month, quarter, year
)
```

---

## 🔄 Task Composition Examples

### Workflow 1: Complete Content Creation Pipeline

```python
from celery import chain, group
from app.tasks import (
    generate_content,
    generate_image,
    generate_video,
    publish_post,
    fetch_analytics
)

# Sequential workflow
workflow = chain(
    generate_content.s(user_id=1, topic="AI", content_type="reel", 
                       platforms=["instagram"]),
    generate_image.s(post_id=None),  # Result auto-passed
    publish_post.s(platforms=["instagram"]),
    fetch_analytics.s(),
)

result = workflow.apply_async()
```

### Workflow 2: Parallel Media Generation

```python
# Generate image and video in parallel
jobs = group([
    generate_image.s(user_id=1, post_id=5, prompt="...", style="modern"),
    generate_video.s(user_id=1, post_id=5, script="...", duration=30),
])

result = jobs.apply_async()
```

### Workflow 3: Batch Processing

```python
# Generate content for multiple users
from celery import group

jobs = group([
    generate_content.s(user_id=uid, topic="AI", 
                      content_type="reel", platforms=["instagram"])
    for uid in [1, 2, 3, 4, 5]
])

results = jobs.apply_async()
```

---

## 📊 Monitoring and Management

### Using Flower Dashboard

1. **Access**: http://localhost:5555
2. **Features**:
   - View active tasks
   - Monitor worker status
   - View task history
   - Inspect task details
   - Pool management

### Command Line Tools

#### Check Status
```bash
python app/tasks/runner.py monitor status
```

#### View Queues
```bash
python app/tasks/runner.py monitor queues
```

#### Health Check
```bash
python app/tasks/runner.py monitor health
```

#### Inspect Task
```bash
python app/tasks/runner.py task inspect <task_id>
```

### Using Celery CLI

```bash
# Inspect active tasks
celery -A app.celery_app inspect active

# Inspect scheduled tasks
celery -A app.celery_app inspect scheduled

# Inspect worker stats
celery -A app.celery_app inspect stats

# Inspect registered tasks
celery -A app.celery_app inspect registered

# Get worker pool status
celery -A app.celery_app inspect pool

# Purge all tasks
celery -A app.celery_app purge
```

---

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Redis
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Celery
CELERY_TIMEZONE=UTC
CELERY_ENABLE_UTC=True
```

### Worker Configuration

```python
# app/celery_app.py

app.conf.update(
    # Task limits
    task_time_limit=30 * 60,      # Hard limit: 30 minutes
    task_soft_time_limit=25 * 60, # Soft limit: 25 minutes
    
    # Concurrency per queue
    # See WORKER_COMMANDS in worker_utils.py
    
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    
    # Task acknowledgment
    task_acks_late=True,  # Ack after task completion
    
    # Retry policy
    task_autoretry_for=(Exception,),
    task_max_retries=3,
)
```

---

## 🐳 Docker Deployment

### docker-compose.yml

```yaml
version: '3.8'

services:
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  celery_content:
    build: .
    command: celery -A app.celery_app worker -l info -n content@%h -Q content --concurrency=2
    depends_on:
      - redis
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/1

  celery_media:
    build: .
    command: celery -A app.celery_app worker -l info -n media@%h -Q media --concurrency=1
    depends_on:
      - redis
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/1

  celery_beat:
    build: .
    command: celery -A app.celery_app beat -l info
    depends_on:
      - redis
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/1

  flower:
    build: .
    command: celery -A app.celery_app flower --port=5555
    ports:
      - "5555:5555"
    depends_on:
      - redis

volumes:
  redis_data:
```

### Start All Services

```bash
docker-compose up -d
```

---

## ❌ Troubleshooting

### Tasks Not Running

1. **Check Redis connection**:
   ```bash
   redis-cli ping
   ```

2. **Check worker logs**:
   ```bash
   celery -A app.celery_app inspect active
   ```

3. **Verify task routing**:
   ```bash
   celery -A app.celery_app inspect registered
   ```

### Worker Keeps Restarting

1. Check task time limits
2. Look for exceptions in logs
3. Verify database connection

### Memory Issues

1. Limit results expiration
2. Configure `result_expires`
3. Use `revoke()` to clean up tasks

### Connection Refused

1. Ensure Redis is running
2. Check connection string
3. Verify firewall rules

---

## 📚 Best Practices

### ✅ DO

- ✓ Use task idempotency (tasks can be safely retried)
- ✓ Store large data in database, not task arguments
- ✓ Set appropriate time limits
- ✓ Monitor task execution
- ✓ Use routing for task isolation
- ✓ Implement error handling and retries
- ✓ Use task chains for sequential operations

### ❌ DON'T

- ✗ Store large objects in task arguments
- ✗ Create tasks with indefinite runtime
- ✗ Send sensitive data through task queue
- ✗ Use blocking operations in tasks
- ✗ Share state between tasks
- ✗ Ignore task failures silently

---

## 📖 File Structure

```
app/
├── celery_app.py                 # Celery configuration
├── tasks/
│   ├── __init__.py              # Task package exports
│   ├── content_tasks.py         # Content generation tasks
│   ├── media_tasks.py           # Image/video generation tasks
│   ├── publish_tasks.py         # Publishing tasks
│   ├── analytics_tasks.py       # Analytics tasks
│   ├── worker_utils.py          # Worker utilities and monitoring
│   ├── broker_utils.py          # Redis/broker utilities
│   └── runner.py                # CLI task runner
```

---

## 🔗 Related Documentation

- [Celery Official Docs](https://docs.celeryproject.io/)
- [Redis Documentation](https://redis.io/documentation)
- [Flower Docs](https://flower.readthedocs.io/)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)

---

## 🎯 Next Steps

1. Set up monitoring with Flower
2. Configure production Redis with persistence
3. Implement custom task error handlers
4. Set up task retry policies
5. Create automated task cleanup
6. Implement rate limiting

---

**Last Updated**: April 2026
**Version**: 1.0.0
