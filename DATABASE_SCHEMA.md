# 📊 Database Schema Documentation

## Overview

The AI Content Platform uses PostgreSQL as the primary data store. This document outlines the complete database schema, relationships, and design decisions.

### Key Design Principles

- **Multi-Tenant**: Isolated data per user/organization
- **Audit Trail**: All modifications tracked with timestamps
- **Soft Deletes**: Deleted records retained for compliance
- **Indexing**: Optimized for common queries
- **Normalization**: Third normal form (3NF)
- **JSONB**: Flexible metadata storage for platform-specific data

---

## Entity-Relationship Diagram

```
users (1) ──→ (many) accounts
users (1) ──→ (many) posts
users (1) ──→ (many) campaigns
users (1) ──→ (many) logs
accounts (1) ──→ (many) posts
accounts (1) ──→ (many) schedules
posts (1) ──→ (many) analytics
posts (1) ──→ (many) duplicates
posts (1) ──→ (many) assets
trends (1) ──→ (many) posts
hashtags (1) ──→ (many) posts (M:N via post_hashtags)
campaigns (1) ──→ (many) posts
```

---

## Table Schemas

### 1. Users Table

**Purpose**: Multi-tenant SaaS user account management

```sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    avatar_url TEXT,
    
    -- Settings
    plan VARCHAR(50) DEFAULT 'free',  -- free, pro, enterprise
    subscription_status VARCHAR(50),    -- active, paused, cancelled
    max_posts_per_day INTEGER DEFAULT 10,
    max_accounts INTEGER DEFAULT 3,
    api_key VARCHAR(200) UNIQUE,
    api_key_hash VARCHAR(255),
    
    -- Organization
    organization_name VARCHAR(255),
    timezone VARCHAR(50) DEFAULT 'UTC',
    language VARCHAR(10) DEFAULT 'en',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    email_verified_at TIMESTAMP WITH TIME ZONE,
    last_login_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    preferences JSONB,  -- UI preferences, default platforms, etc.
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    INDEX idx_email (email),
    INDEX idx_username (username),
    INDEX idx_api_key (api_key),
    INDEX idx_created_at (created_at),
    INDEX idx_is_active (is_active)
);
```

**Relationships**:
- One-to-Many: posts, accounts, campaigns, logs

**Key Features**:
- Multi-tenant isolation via user_id
- API key support for programmatic access
- Subscription/plan management
- Timezone and language preferences
- Soft delete via deleted_at

---

### 2. Accounts Table

**Purpose**: Social media accounts linked to users

```sql
CREATE TABLE accounts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    
    -- Platform Info
    platform VARCHAR(50) NOT NULL,  -- instagram, tiktok, youtube, facebook, x, linkedin, telegram
    platform_user_id VARCHAR(255) NOT NULL,
    username VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    avatar_url TEXT,
    bio TEXT,
    
    -- Authentication
    access_token VARCHAR(2000),
    refresh_token VARCHAR(2000),
    token_type VARCHAR(50),
    token_expires_at TIMESTAMP WITH TIME ZONE,
    token_scopes JSONB,
    
    -- Account Status
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    is_shadowbanned BOOLEAN DEFAULT FALSE,
    shadowban_detected_at TIMESTAMP WITH TIME ZONE,
    
    -- Metrics
    followers INTEGER DEFAULT 0,
    engagement_rate FLOAT DEFAULT 0.0,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    
    -- Platform-Specific Data
    metadata JSONB,  -- follower growth, engagement metrics, etc.
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE (user_id, platform, platform_user_id),
    INDEX idx_user_id (user_id),
    INDEX idx_platform (platform),
    INDEX idx_is_active (is_active),
    INDEX idx_is_shadowbanned (is_shadowbanned)
);
```

**Relationships**:
- Many-to-One: users (parent)
- One-to-Many: posts, schedules

**Key Features**:
- OAuth token management with refresh
- Shadowban detection
- Per-platform metrics tracking
- Account health monitoring

---

### 3. Posts Table

**Purpose**: Generated and published content

```sql
CREATE TABLE posts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    account_id BIGINT REFERENCES accounts(id),
    
    -- Content
    title VARCHAR(500),
    script TEXT,
    caption TEXT,
    hooks JSONB,  -- Array of hooks generated
    cta_text VARCHAR(500),
    
    -- Media References
    primary_asset_id BIGINT REFERENCES assets(id),
    asset_ids BIGINT[],  -- Array of asset IDs
    
    -- Classification
    category VARCHAR(100),  -- motivation, business, education, entertainment, etc.
    content_type VARCHAR(50),  -- reel, short, carousel, story, post, long-form
    language VARCHAR(10),
    
    -- Platform & Publishing
    platforms JSONB,  -- {'instagram': {...}, 'tiktok': {...}}
    platform_post_ids JSONB,  -- platform-specific post IDs after publishing
    
    -- Quality & Analytics
    quality_score FLOAT DEFAULT 0.0,
    engagement_prediction FLOAT DEFAULT 0.0,
    estimated_reach INTEGER,
    
    -- Trend & Campaign
    trend_id BIGINT REFERENCES trends(id),
    campaign_id BIGINT REFERENCES campaigns(id),
    
    -- Status
    status VARCHAR(50) DEFAULT 'draft',  -- draft, review, approved, scheduled, published, archived
    review_notes TEXT,
    reviewer_id BIGINT REFERENCES users(id),
    
    -- Publishing Timeline
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    scheduled_at TIMESTAMP WITH TIME ZONE,
    published_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    metadata JSONB,
    
    INDEX idx_user_id (user_id),
    INDEX idx_account_id (account_id),
    INDEX idx_status (status),
    INDEX idx_category (category),
    INDEX idx_created_at (created_at),
    INDEX idx_published_at (published_at),
    INDEX idx_trend_id (trend_id),
    INDEX idx_campaign_id (campaign_id)
);
```

**Relationships**:
- Many-to-One: users, accounts, trends, campaigns
- One-to-Many: analytics, duplicates, post_hashtags
- Many-to-One: assets (primary), assets (array)

**Key Features**:
- Multi-platform support with platform-specific data
- Quality scoring and engagement prediction
- Status workflow (draft → review → published)
- Trend and campaign association
- JSONB hook and platform data

---

### 4. Analytics Table

**Purpose**: Track post performance across platforms

```sql
CREATE TABLE analytics (
    id BIGSERIAL PRIMARY KEY,
    post_id BIGINT NOT NULL REFERENCES posts(id),
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    
    -- Platform & Post IDs
    platform VARCHAR(50) NOT NULL,
    platform_post_id VARCHAR(255),
    platform_account_id VARCHAR(255),
    
    -- Engagement Metrics
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    click_count INTEGER DEFAULT 0,
    
    -- Derived Metrics
    engagement_rate FLOAT DEFAULT 0.0,
    comment_rate FLOAT DEFAULT 0.0,
    share_rate FLOAT DEFAULT 0.0,
    ctr FLOAT DEFAULT 0.0,  -- Click-through rate
    
    -- Video-Specific Metrics
    watch_time_total INTEGER DEFAULT 0,  -- seconds
    watch_time_avg FLOAT DEFAULT 0.0,    -- seconds
    completion_rate FLOAT DEFAULT 0.0,   -- percentage
    skip_rate_3s FLOAT DEFAULT 0.0,
    skip_rate_10s FLOAT DEFAULT 0.0,
    skip_rate_30s FLOAT DEFAULT 0.0,
    
    -- Demographic Insights
    top_countries JSONB,  -- Top 5 countries
    top_cities JSONB,     -- Top 5 cities
    audience_age JSONB,   -- Age distribution
    audience_gender JSONB, -- Gender distribution
    
    -- Timing
    tracked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    synced_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    metadata JSONB,
    
    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    INDEX idx_post_id (post_id),
    INDEX idx_account_id (account_id),
    INDEX idx_platform (platform),
    INDEX idx_tracked_at (tracked_at),
    INDEX idx_engagement_rate (engagement_rate),
    UNIQUE (post_id, platform)
);
```

**Relationships**:
- Many-to-One: posts, accounts

**Key Features**:
- Comprehensive engagement tracking
- Video-specific metrics (completion, skip rates)
- Demographic insights
- Time-series data for performance analysis

---

### 5. Trends Table

**Purpose**: Store discovered and tracked trends

```sql
CREATE TABLE trends (
    id BIGSERIAL PRIMARY KEY,
    
    -- Trend Info
    title VARCHAR(500) NOT NULL,
    description TEXT,
    slug VARCHAR(500) UNIQUE,
    
    -- Metrics
    trend_score FLOAT DEFAULT 0.0,     -- 0-100
    viral_score FLOAT DEFAULT 0.0,     -- 0-100
    growth_rate FLOAT DEFAULT 0.0,     -- percentage
    saturation_level FLOAT DEFAULT 0.0, -- 0-100
    
    -- Ranking
    rank INTEGER,
    rank_change INTEGER,
    
    -- Source Info
    source VARCHAR(100),  -- google_trends, youtube, reddit, tiktok, instagram, twitter
    primary_source VARCHAR(100),
    secondary_sources JSONB,
    
    -- Geographic & Language
    countries JSONB,  -- Array of country codes
    languages JSONB,  -- Array of language codes
    
    -- Temporal
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    trend_starts_at TIMESTAMP WITH TIME ZONE,
    trend_peaks_at TIMESTAMP WITH TIME ZONE,
    trend_ends_at TIMESTAMP WITH TIME ZONE,
    
    -- Content Guidance
    recommended_platforms JSONB,  -- ['instagram', 'tiktok', ...]
    recommended_format VARCHAR(50),  -- reel, short, story, post
    recommended_duration_min INTEGER,
    recommended_duration_max INTEGER,
    
    -- Related Data
    related_hashtags JSONB,
    related_audio JSONB,
    related_trends BIGINT[],
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_rising BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    metadata JSONB,
    
    INDEX idx_title (title),
    INDEX idx_trend_score (trend_score),
    INDEX idx_viral_score (viral_score),
    INDEX idx_detected_at (detected_at),
    INDEX idx_is_active (is_active),
    INDEX idx_is_rising (is_rising)
);
```

**Relationships**:
- One-to-Many: posts

**Key Features**:
- Multi-source trend tracking
- Saturation and growth metrics
- Geographic and language segmentation
- Platform and content recommendations
- Trend lifecycle tracking

---

### 6. Hashtags Table

**Purpose**: Hashtag tracking and analytics

```sql
CREATE TABLE hashtags (
    id BIGSERIAL PRIMARY KEY,
    
    -- Hashtag Info
    tag VARCHAR(200) UNIQUE NOT NULL,
    display_tag VARCHAR(200),
    description TEXT,
    
    -- Metrics
    post_count INTEGER DEFAULT 0,
    engagement_total BIGINT DEFAULT 0,
    avg_engagement FLOAT DEFAULT 0.0,
    reach_total BIGINT DEFAULT 0,
    avg_reach FLOAT DEFAULT 0.0,
    
    -- Performance
    trending_score FLOAT DEFAULT 0.0,
    is_trending BOOLEAN DEFAULT FALSE,
    trend_rank INTEGER,
    
    -- Classification
    category VARCHAR(100),
    platform VARCHAR(50),  -- Global or specific platform
    
    -- Time Data
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE,
    peaks_at_hour INTEGER,  -- 0-23 UTC
    peaks_at_day VARCHAR(10),  -- Monday, Tuesday, etc.
    
    -- Metadata
    metadata JSONB,
    
    INDEX idx_tag (tag),
    INDEX idx_trending_score (trending_score),
    INDEX idx_is_trending (is_trending),
    INDEX idx_category (category),
    INDEX idx_last_used_at (last_used_at)
);

-- Junction table for posts and hashtags (M:N relationship)
CREATE TABLE post_hashtags (
    post_id BIGINT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    hashtag_id BIGINT NOT NULL REFERENCES hashtags(id),
    used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (post_id, hashtag_id),
    INDEX idx_hashtag_id (hashtag_id)
);
```

**Relationships**:
- Many-to-Many: posts via post_hashtags

**Key Features**:
- Hashtag performance tracking
- Trending status and rank
- Optimal posting time detection
- Platform-specific hashtag analytics

---

### 7. Assets Table

**Purpose**: Media assets (images, videos, audio)

```sql
CREATE TABLE assets (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    
    -- Asset Info
    filename VARCHAR(500) NOT NULL,
    mime_type VARCHAR(100),
    asset_type VARCHAR(50),  -- image, video, audio
    
    -- Storage
    s3_bucket VARCHAR(255),
    s3_key VARCHAR(500),
    s3_url TEXT,
    file_size BIGINT,  -- bytes
    duration INTEGER,  -- seconds (for video/audio)
    
    -- Metadata
    width INTEGER,
    height INTEGER,
    fps FLOAT,  -- frames per second (video)
    resolution VARCHAR(50),  -- 1080p, 4K, etc.
    codec VARCHAR(100),
    bitrate VARCHAR(50),
    
    -- Content Analysis
    has_text BOOLEAN DEFAULT FALSE,
    has_faces BOOLEAN DEFAULT FALSE,
    has_objects ARRAY,  -- detected objects
    dominant_colors JSONB,
    sentiment_score FLOAT,
    
    -- License & Rights
    source VARCHAR(100),  -- pexels, pixabay, user_uploaded, generated
    license_type VARCHAR(50),  -- free, cc0, paid
    attribution_required BOOLEAN DEFAULT FALSE,
    attribution_text TEXT,
    
    -- Status
    processing_status VARCHAR(50),  -- pending, processing, ready, failed
    processing_error TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Temporal
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    metadata JSONB,
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_id (user_id),
    INDEX idx_asset_type (asset_type),
    INDEX idx_source (source),
    INDEX idx_created_at (created_at),
    INDEX idx_processing_status (processing_status)
);
```

**Relationships**:
- Many-to-One: users (parent)
- One-to-Many: posts

**Key Features**:
- MinIO integration for storage
- Content analysis and metadata
- License and attribution tracking
- Processing status management

---

### 8. Schedules Table

**Purpose**: Publishing schedule management

```sql
CREATE TABLE schedules (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    post_id BIGINT NOT NULL REFERENCES posts(id),
    
    -- Schedule Info
    platform VARCHAR(50) NOT NULL,  -- Target platform for this schedule
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Publishing Details
    publish_method VARCHAR(50),  -- auto, approved, manual
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending',  -- pending, processing, published, failed, cancelled
    published_at TIMESTAMP WITH TIME ZONE,
    published_url TEXT,
    platform_response JSONB,  -- Platform API response
    
    -- Error Tracking
    error_message TEXT,
    error_code VARCHAR(100),
    
    -- Metadata
    metadata JSONB,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (post_id) REFERENCES posts(id),
    INDEX idx_scheduled_time (scheduled_time),
    INDEX idx_status (status),
    INDEX idx_platform (platform),
    INDEX idx_user_id (user_id)
);
```

**Relationships**:
- Many-to-One: users, accounts, posts

**Key Features**:
- Timezone-aware scheduling
- Multi-platform scheduling support
- Retry logic with tracking
- Platform API response storage

---

### 9. Duplicates Table

**Purpose**: Track duplicate content detection

```sql
CREATE TABLE duplicates (
    id BIGSERIAL PRIMARY KEY,
    primary_post_id BIGINT NOT NULL REFERENCES posts(id),
    duplicate_post_id BIGINT NOT NULL REFERENCES posts(id),
    
    -- Detection Method
    detection_method VARCHAR(50),  -- embedding, image_hash, text_similarity
    similarity_score FLOAT NOT NULL,  -- 0-1
    confidence FLOAT,
    
    -- Evidence
    matching_fields JSONB,  -- Which fields matched
    hash_value VARCHAR(255),  -- Image/video hash
    text_hash VARCHAR(255),
    
    -- Action Taken
    action VARCHAR(50),  -- warning, blocked, merged, archived
    resolution_notes TEXT,
    
    -- Temporal
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    metadata JSONB,
    
    FOREIGN KEY (primary_post_id) REFERENCES posts(id),
    FOREIGN KEY (duplicate_post_id) REFERENCES posts(id),
    INDEX idx_primary_post_id (primary_post_id),
    INDEX idx_duplicate_post_id (duplicate_post_id),
    INDEX idx_similarity_score (similarity_score),
    INDEX idx_detected_at (detected_at)
);
```

**Relationships**:
- Many-to-One: posts (two relationships)

**Key Features**:
- Multiple detection methods
- Similarity scoring
- Action tracking
- Resolution history

---

### 10. Campaigns Table

**Purpose**: Marketing and promotional campaigns

```sql
CREATE TABLE campaigns (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    
    -- Campaign Info
    name VARCHAR(255) NOT NULL,
    description TEXT,
    slug VARCHAR(255) UNIQUE,
    
    -- Campaign Details
    objective VARCHAR(100),  -- awareness, engagement, conversion, retention
    campaign_type VARCHAR(50),  -- product_launch, seasonal, promotional, retention
    
    -- Targeting
    target_audience JSONB,  -- age, gender, interests, locations
    target_platforms JSONB,  -- ['instagram', 'tiktok', ...]
    target_countries JSONB,
    
    -- Performance Goals
    goal_metric VARCHAR(50),  -- views, engagements, conversions
    goal_value INTEGER,
    
    -- Timeline
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Budget (if applicable)
    budget DECIMAL(10, 2),
    spent DECIMAL(10, 2) DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Performance Metrics
    total_posts INTEGER DEFAULT 0,
    total_views BIGINT DEFAULT 0,
    total_engagements BIGINT DEFAULT 0,
    total_conversions INTEGER DEFAULT 0,
    roi FLOAT DEFAULT 0.0,
    
    -- Status
    status VARCHAR(50) DEFAULT 'draft',  -- draft, active, paused, completed, archived
    
    -- Metadata
    metadata JSONB,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_start_date (start_date),
    INDEX idx_objective (objective)
);
```

**Relationships**:
- Many-to-One: users (parent)
- One-to-Many: posts

**Key Features**:
- Campaign objectives and metrics
- Budget tracking (optional)
- ROI calculation
- Audience targeting

---

### 11. Logs Table

**Purpose**: Audit trail and operational logging

```sql
CREATE TABLE logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    
    -- Log Context
    entity_type VARCHAR(100),  -- post, account, campaign, etc.
    entity_id BIGINT,
    
    -- Action
    action VARCHAR(100),  -- create, read, update, delete, publish, etc.
    action_category VARCHAR(50),  -- user_action, system_action, error
    
    -- Details
    description TEXT,
    old_values JSONB,  -- Previous values on update
    new_values JSONB,  -- New values on update
    
    -- Request Context
    ip_address INET,
    user_agent TEXT,
    api_key_used VARCHAR(200),
    
    -- Status
    status VARCHAR(50),  -- success, failure, warning
    error_message TEXT,
    error_code VARCHAR(100),
    error_stack_trace TEXT,
    
    -- Metadata
    metadata JSONB,
    
    -- Temporal
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_user_id (user_id),
    INDEX idx_entity_type (entity_type),
    INDEX idx_entity_id (entity_id),
    INDEX idx_action (action),
    INDEX idx_created_at (created_at),
    INDEX idx_status (status)
);
```

**Relationships**:
- Many-to-One: users (parent)

**Key Features**:
- Comprehensive audit trail
- Error tracking
- User action tracking
- Compliance logging

---

## Indexes Strategy

### Performance Indexes
- User ID indexes on all user-related tables
- Status indexes on workflow tables (posts, schedules)
- Timestamp indexes for time-range queries
- Created_at indexes for pagination

### Compound Indexes
```sql
CREATE INDEX idx_posts_user_status ON posts(user_id, status);
CREATE INDEX idx_analytics_post_date ON analytics(post_id, tracked_at);
CREATE INDEX idx_schedules_time_status ON schedules(scheduled_time, status);
```

---

## Query Patterns

### 1. Get User's Posts (Last 30 Days)
```sql
SELECT p.* 
FROM posts p
WHERE p.user_id = $1 
  AND p.created_at > NOW() - INTERVAL '30 days'
ORDER BY p.created_at DESC;
```

### 2. Get Analytics for Post
```sql
SELECT a.*
FROM analytics a
WHERE a.post_id = $1
ORDER BY a.tracked_at DESC;
```

### 3. Find Duplicate Content
```sql
SELECT d.*
FROM duplicates d
WHERE d.primary_post_id = $1 
  AND d.similarity_score > 0.8;
```

### 4. Get Trending Hashtags
```sql
SELECT h.*
FROM hashtags h
WHERE h.is_trending = TRUE
  AND h.platform = $1
ORDER BY h.trending_score DESC
LIMIT 20;
```

### 5. Get Scheduled Posts
```sql
SELECT s.*
FROM schedules s
WHERE s.account_id = $1
  AND s.scheduled_time BETWEEN $2 AND $3
  AND s.status = 'pending'
ORDER BY s.scheduled_time ASC;
```

---

## Data Integrity Constraints

### Cascade Rules
- User deletion → cascades to posts, accounts, campaigns, logs (soft delete)
- Post deletion → cascades to analytics, duplicates, schedules (soft delete)
- Account deletion → cascades to schedules, analytics (soft delete)

### Referential Integrity
- All foreign keys enforce referential integrity
- Updated_at timestamps auto-update via triggers
- Deleted_at enables soft deletes

---

## Backup & Recovery

### Backup Strategy
- Daily full backups
- Hourly transaction log backups
- Point-in-time recovery to 30 days

### Recovery Procedures
- Restore to new database
- Verify data integrity
- Point-in-time restore via timestamps

---

## Performance Tuning

### Partitioning (Future)
```sql
-- Partition analytics by month
CREATE TABLE analytics_2024_01 PARTITION OF analytics
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

### Materialized Views (Future)
```sql
CREATE MATERIALIZED VIEW user_engagement_summary AS
SELECT u.id, COUNT(p.id) as post_count, 
       COALESCE(SUM(a.views), 0) as total_views
FROM users u
LEFT JOIN posts p ON u.id = p.user_id
LEFT JOIN analytics a ON p.id = a.post_id
GROUP BY u.id;
```

---

## Monitoring & Maintenance

### Key Metrics to Monitor
- Database size growth
- Query performance (slow query log)
- Connection pool utilization
- Index fragmentation
- Table bloat from deletes

### Maintenance Tasks
- VACUUM ANALYZE weekly
- Index maintenance monthly
- Statistics update daily
- Garbage collection of soft deletes quarterly
