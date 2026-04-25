# 🚀 Production Deployment Guide

## Auto-Fetch Integration — Complete Setup

This guide covers the complete setup for the AI Content Automation platform with real-time engagement data collection.

---

## 📋 Prerequisites

### System Requirements
- **Python**: 3.12+
- **PostgreSQL**: 13+
- **Redis**: 6+
- **Docker**: 20+ (optional but recommended)
- **Platform API Keys**: YouTube, Instagram, TikTok, etc.

### Platform API Access
| Platform | API | Access Level | Cost |
|----------|-----|--------------|------|
| YouTube | Analytics API | Free (10k units/day) | Free |
| Instagram | Graph API | Business Account | Free |
| TikTok | Marketing API | Business Account | Free |
| Facebook | Graph API | Page Access Token | Free |
| Twitter/X | API v2 | Developer Account | Free |
| LinkedIn | Marketing API | Developer Account | Free |

---

## 🔧 Configuration

### 1. Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/content_db

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Platform API Keys (REQUIRED for production)
YOUTUBE_API_KEY=your_youtube_api_key_here
INSTAGRAM_ACCESS_TOKEN=your_instagram_token_here
TIKTOK_ACCESS_TOKEN=your_tiktok_token_here
FACEBOOK_PAGE_ACCESS_TOKEN=your_facebook_token_here
X_BEARER_TOKEN=your_twitter_bearer_token_here
LINKEDIN_ACCESS_TOKEN=your_linkedin_token_here

# Application
DEBUG=false
ENVIRONMENT=production
```

### 2. Get Platform API Keys

#### YouTube Analytics API
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project → Enable YouTube Data API v3
3. Create API key → Add to `.env`

#### Instagram Graph API
1. [Meta for Developers](https://developers.facebook.com/)
2. Create app → Add Instagram Basic Display
3. Generate access token → Add to `.env`

#### TikTok Marketing API
1. [TikTok Developers](https://developers.tiktok.com/)
2. Create app → Marketing API
3. Generate access token → Add to `.env`

---

## 🐳 Docker Deployment

### Quick Start
```bash
# Clone repository
git clone <repository-url>
cd ai-content-fully-automated

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker-compose up -d

# Initialize database
docker-compose exec app python scripts/init_db.py

# Load ML models
docker-compose exec app python scripts/load_models.py

# Start Celery workers
docker-compose exec worker celery -A app.tasks.worker worker --loglevel=info

# Start Celery beat scheduler
docker-compose exec worker celery -A app.tasks.worker beat --loglevel=info
```

### Service Architecture
```
┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │  Celery Worker  │
│   (Port 8000)   │    │  (Auto-fetch)   │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          └──────────┬───────────┘
                     │
          ┌─────────────────────┐
          │    PostgreSQL       │
          │    Redis            │
          │    MinIO            │
          └─────────────────────┘
```

---

## 🔄 Manual Testing

### Test API Integration
```bash
# Test with mock data
python scripts/test_real_api_integration.py --mock-only

# Test with real APIs (requires .env keys)
python scripts/test_real_api_integration.py --use-real-apis
```

### Test Auto-Fetch Tasks
```bash
# Trigger manual data collection
curl -X POST http://localhost:8000/api/v1/content/engagement/auto-fetch

# Check task status
curl http://localhost:8000/api/v1/content/engagement/monitoring
```

### Test Model Retraining
```bash
# Manual retraining trigger
curl -X POST http://localhost:8000/api/v1/content/engagement/retrain-model
```

---

## 📊 Monitoring & Maintenance

### Health Checks
```bash
# Application health
curl http://localhost:8000/api/v1/health

# Auto-fetch monitoring
curl http://localhost:8000/api/v1/content/engagement/monitoring

# Data collection stats
curl http://localhost:8000/api/v1/content/engagement/data/stats
```

### Scheduled Tasks Status
- **Auto-fetch**: Every 6 hours (collects last 24h data)
- **Follower updates**: Daily at 4 AM UTC
- **Model retraining**: Daily at 5 AM UTC (if 100+ new samples)

### Logs Monitoring
```bash
# Application logs
docker-compose logs -f app

# Celery worker logs
docker-compose logs -f worker

# Auto-fetch specific logs
docker-compose logs worker | grep "auto_fetch"
```

---

## 🚨 Troubleshooting

### Common Issues

#### 1. API Rate Limits
```
Error: Rate limit exceeded
```
**Solution**: Check `/api/v1/content/engagement/monitoring` for quota status

#### 2. Missing API Keys
```
Error: No API key configured for platform
```
**Solution**: Add keys to `.env` file and restart services

#### 3. Database Connection
```
Error: Can't connect to database
```
**Solution**:
```bash
# Check database status
docker-compose ps db

# Restart database
docker-compose restart db
```

#### 4. Celery Tasks Not Running
```
Error: Tasks not executing
```
**Solution**:
```bash
# Check Celery status
docker-compose ps worker

# Restart Celery
docker-compose restart worker
```

---

## 📈 Performance Tuning

### Rate Limiting Configuration
Edit `app/utils/rate_limiter.py`:
```python
PLATFORM_RATE_LIMITS = {
    "youtube": {"calls": 10000, "period": 86400},  # Conservative defaults
    "instagram": {"calls": 200, "period": 3600},
    # Adjust based on your API quotas
}
```

### Database Optimization
```sql
-- Create indexes for performance
CREATE INDEX idx_analytics_post_platform ON analytics(post_id, platform);
CREATE INDEX idx_analytics_timestamp ON analytics(timestamp);
CREATE INDEX idx_posts_user_published ON posts(user_id, published_at);
```

### Redis Configuration
```bash
# Increase Redis memory if needed
docker-compose exec redis redis-cli CONFIG SET maxmemory 512mb
```

---

## 🔒 Security Best Practices

### API Key Management
- Store keys in environment variables only
- Rotate keys regularly
- Use separate keys for development/production
- Monitor API usage for anomalies

### Database Security
```sql
-- Create read-only user for analytics
CREATE USER analytics_user WITH PASSWORD 'secure_password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_user;
```

### Network Security
- Run behind reverse proxy (nginx)
- Enable HTTPS
- Restrict database access to internal network
- Use Redis password in production

---

## 📚 API Reference

### Auto-Fetch Endpoints

#### Trigger Data Collection
```bash
POST /api/v1/content/engagement/auto-fetch
# Body: {"user_id": 123, "background": true}
```

#### Update Followers
```bash
POST /api/v1/content/engagement/update-followers
# Body: {"user_id": 123, "background": true}
```

#### Retrain Model
```bash
POST /api/v1/content/engagement/retrain-model
# Body: {"background": true}
```

#### Monitoring Dashboard
```bash
GET /api/v1/content/engagement/monitoring
# Returns: data collection stats, API quotas, task status
```

---

## 🎯 Production Readiness Checklist

- [ ] API keys configured in `.env`
- [ ] Database initialized with `init_db.py`
- [ ] ML models loaded with `load_models.py`
- [ ] All services running (`docker-compose ps`)
- [ ] Health checks passing
- [ ] Auto-fetch tasks scheduled
- [ ] Monitoring endpoints working
- [ ] Rate limits configured appropriately
- [ ] Backup strategy in place
- [ ] SSL certificates configured
- [ ] Monitoring alerts set up

---

## 🆘 Support

### Getting Help
1. Check logs: `docker-compose logs -f`
2. Test APIs: `python scripts/test_real_api_integration.py`
3. Health check: `curl http://localhost:8000/api/v1/health`
4. Documentation: Check inline code comments

### Common Support Issues
- **Platform API changes**: Update `app/services/analytics_service.py`
- **Rate limit issues**: Adjust `app/utils/rate_limiter.py`
- **Model performance**: Retrain with more data
- **Database performance**: Add indexes as needed

---

*Last updated: January 2025*

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
