# AI Content Platform Architecture

## System Overview

```
app-core        → API + all engines
worker          → async/background jobs
infra           → PostgreSQL + Redis + MinIO
vector-db       → Chroma / Qdrant
monitoring      → Prometheus + Grafana + Loki
```

## Directory Structure

### /app - Main Application
- **api/** - FastAPI routes and endpoints
- **core/** - Core configuration, database, Redis, MinIO clients
- **models/** - SQLAlchemy ORM models
- **schemas/** - Pydantic request/response schemas
- **services/** - Business logic services
- **engines/** - 60+ specialized content generation engines
- **utils/** - Logging, validation, exceptions

### /worker - Celery Workers
- **tasks/** - Celery task definitions
  - content_tasks.py - Content generation
  - publishing_tasks.py - Publishing workflows
  - analytics_tasks.py - Analytics tracking
  - trend_tasks.py - Trend analysis
- **queues/** - Queue routing and configuration
- **schedulers/** - Celery Beat periodic task scheduling

### /infra - Infrastructure
- **docker/** - Dockerfile and Docker compose
- **nginx/** - Nginx reverse proxy configuration
- **monitoring/** - Prometheus and Grafana configs

### /config - Configuration
- database.sql - PostgreSQL schema

### /scripts - Utility Scripts
- init_db.py - Database initialization
- start_worker.sh - Start Celery worker
- start_beat.sh - Start Celery Beat scheduler
- load_models.py - Pre-load ML models

### /docs - Documentation
- Architecture documentation
- API documentation
- Setup guides

## Key Technologies

- **Framework**: FastAPI
- **Task Queue**: Celery
- **Message Broker**: Redis
- **Database**: PostgreSQL
- **Object Storage**: MinIO
- **Vector DB**: Chroma / Qdrant
- **LLM Integration**: Ollama (Llamaa, Mistral)
- **Reverse Proxy**: Nginx
- **Monitoring**: Prometheus + Grafana + Loki

## CPU-Only Optimization

- No GPU dependencies assumed
- Model loading/unloading on demand  
- Sequential heavy job processing
- Resource pooling and caching

## Performance Targets

- Single language content: <2 min
- Multi-language content: <5-7 min
- Image generation: <10 sec
- Script generation: <15 sec

## Security

- JWT authentication
- OAuth for social platforms
- Encrypted credentials
- Role-based access control

## Scalability

- Horizontal worker scaling
- Queue-based load distribution
- Database connection pooling
- Redis caching layer
- MinIO distributed storage
