# Deployment Guide

## Prerequisites

- Server with Docker & Docker Compose
- Domain name with SSL certificate
- API keys for social platforms
- Sufficient storage (MinIO buckets)

## Environment Setup

1. SSH into production server
2. Clone repository
3. Configure .env for production:
   ```bash
   cp .env.example .env
   # Edit .env with production values
   ```

## Docker Compose Deployment

1. Build images:
   ```bash
   docker-compose build
   ```

2. Start services:
   ```bash
   docker-compose up -d
   ```

3. Run migrations:
   ```bash
   docker-compose exec app python scripts/init_db.py --seed
   ```

4. Verify health:
   ```bash
   curl http://localhost/health
   ```

## SSL/HTTPS Configuration

Update `infra/nginx/nginx.conf` with SSL certificate paths:

```nginx
listen 443 ssl;
ssl_certificate /etc/letsencrypt/live/domain.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/domain.com/privkey.pem;
```

## Scaling Workers

Add more Celery workers:

```bash
docker-compose up -d --scale worker=4
```

## Monitoring

- Prometheus: http://your-domain:9090
- Grafana: http://your-domain:3000
- API Docs: http://your-domain:80/docs

## Backup & Recovery

### Database Backup
```bash
docker-compose exec postgres pg_dump -U postgres content_db > backup.sql
```

### Restore
```bash
docker-compose exec -T postgres psql -U postgres content_db < backup.sql
```

### MinIO Backup
```bash
docker-compose exec minio mc mirror minio/content-assets backup/
```

## Troubleshooting

### Check Logs
```bash
docker-compose logs -f app
docker-compose logs -f worker
docker-compose logs -f postgres
```

### Restart Services
```bash
docker-compose restart app worker
```

### Clear Cache
```bash
docker-compose exec redis redis-cli FLUSHALL
```

## Performance Tuning

- Increase worker concurrency in docker-compose.yml
- Tune PostgreSQL connection pool
- Configure Redis eviction policy
- Monitor Prometheus metrics
