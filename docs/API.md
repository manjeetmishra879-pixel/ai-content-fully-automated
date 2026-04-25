# API Reference

## Base URL
```
http://localhost/api/v1
```

## Authentication
All endpoints require JWT token in Authorization header:
```
Authorization: Bearer <token>
```

## Content Endpoints

### Generate Content
```
POST /content/generate
Content-Type: application/json

{
  "title": "Viral Marketing Tips",
  "category": "marketing",
  "platform_targets": ["instagram", "tiktok", "youtube"]
}

Response: 201 Created
{
  "id": 1,
  "title": "Viral Marketing Tips",
  "category": "marketing",
  "status": "processing",
  "task_id": "abc123..."
}
```

### Get Content
```
GET /content/{content_id}

Response: 200 OK
{
  "id": 1,
  "title": "Viral Marketing Tips",
  "script": "...",
  "hooks": ["..."],
  "quality_score": 87.5,
  "status": "published"
}
```

### Update Content
```
PUT /content/{content_id}
Content-Type: application/json

{
  "title": "Updated Title",
  "script": "Updated script..."
}

Response: 200 OK
```

### Delete Content
```
DELETE /content/{content_id}

Response: 204 No Content
```

### List Content
```
GET /content?skip=0&limit=20&category=marketing&status=published

Response: 200 OK
{
  "items": [...],
  "total": 100
}
```

## Trend Endpoints

### Get Trends
```
GET /trends?sort_by=viral_score&limit=10

Response: 200 OK
{
  "trends": [
    {
      "id": 1,
      "title": "AI Content Creation",
      "source": "google_trends",
      "trend_score": 95.2,
      "viral_score": 88.5,
      "rank": 1
    }
  ]
}
```

### Get Viral Radar
```
GET /trends/viral-radar

Response: 200 OK
{
  "x_trending": [...],
  "google_breakout": [...],
  "instagram_audio": [...],
  "tiktok_rising": [...]
}
```

## Publishing Endpoints

### Publish Content
```
POST /publish
Content-Type: application/json

{
  "content_id": 1,
  "platforms": ["instagram", "tiktok"],
  "publish_immediately": true
}

Response: 202 Accepted
{
  "status": "publishing",
  "task_id": "def456..."
}
```

### Schedule Publishing
```
POST /publish/schedule
Content-Type: application/json

{
  "content_id": 1,
  "platforms": ["instagram", "youtube"],
  "scheduled_time": "2024-04-26T10:00:00Z"
}

Response: 201 Created
{
  "id": 1,
  "content_id": 1,
  "scheduled_time": "2024-04-26T10:00:00Z"
}
```

### Get Publishing Schedule
```
GET /publish/schedule?platform=instagram&status=pending

Response: 200 OK
{
  "schedule": [...]
}
```

### Get Publishing History
```
GET /publish/history?limit=50

Response: 200 OK
{
  "history": [...]
}
```

## Analytics Endpoints

### Dashboard Metrics
```
GET /analytics/dashboard

Response: 200 OK
{
  "total_views": 1000000,
  "total_engagement": 50000,
  "avg_engagement_rate": 5.0,
  "trending_topics": [...],
  "performance_by_platform": {...}
}
```

### Content Analytics
```
GET /analytics/content/{content_id}

Response: 200 OK
{
  "views": 10000,
  "likes": 500,
  "comments": 100,
  "shares": 50,
  "engagement_rate": 6.5,
  "watch_time_avg": 45.2
}
```

### Platform Analytics
```
GET /analytics/platform/{platform}?days=30

Response: 200 OK
{
  "platform": "instagram",
  "period": "30 days",
  "total_posts": 50,
  "total_views": 500000,
  "avg_engagement": 3.2,
  "top_performing": [...]
}
```

## Account Endpoints

### Add Account
```
POST /accounts
Content-Type: application/json

{
  "platform": "instagram",
  "username": "myusername",
  "access_token": "token..."
}

Response: 201 Created
{
  "id": 1,
  "platform": "instagram",
  "username": "myusername",
  "is_active": true
}
```

### List Accounts
```
GET /accounts

Response: 200 OK
{
  "accounts": [...]
}
```

### Remove Account
```
DELETE /accounts/{account_id}

Response: 204 No Content
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters",
  "errors": [...]
}
```

### 401 Unauthorized
```json
{
  "detail": "Invalid or expired token"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 60
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error",
  "request_id": "abc123..."
}
```

## Rate Limiting

- **Per IP**: 1000 requests/hour
- **Per API Key**: 10000 requests/hour
- **Per User**: Unlimited (with auth)

## Webhooks

Subscribe to content events:
```
POST /webhooks
{
  "url": "https://your-domain.com/webhook",
  "events": ["content_published", "analytics_updated"]
}
```
