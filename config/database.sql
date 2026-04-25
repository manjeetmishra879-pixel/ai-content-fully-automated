-- Database initialization script

-- Create schemas
CREATE SCHEMA IF NOT EXISTS public;

-- Contents table
CREATE TABLE contents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    script TEXT,
    hooks JSONB,
    captions JSONB,
    hashtags JSONB,
    category VARCHAR(50),
    platform_targets JSONB,
    quality_score FLOAT DEFAULT 0.0,
    engagement_prediction FLOAT DEFAULT 0.0,
    status VARCHAR(50) DEFAULT 'draft',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    INDEX idx_category (category),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);

-- Accounts table
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    platform VARCHAR(50) NOT NULL,
    username VARCHAR(255),
    account_id VARCHAR(255) UNIQUE,
    access_token VARCHAR(1000),
    refresh_token VARCHAR(1000),
    token_expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    INDEX idx_platform (platform),
    INDEX idx_user_id (user_id)
);

-- Analytics table
CREATE TABLE analytics (
    id SERIAL PRIMARY KEY,
    content_id INTEGER NOT NULL REFERENCES contents(id),
    platform_post_id VARCHAR(255) UNIQUE,
    platform VARCHAR(50),
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    watch_time_avg FLOAT DEFAULT 0.0,
    skip_rate FLOAT DEFAULT 0.0,
    ctr FLOAT DEFAULT 0.0,
    engagement_rate FLOAT DEFAULT 0.0,
    metadata JSONB,
    tracked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    INDEX idx_content_id (content_id),
    INDEX idx_platform (platform)
);

-- Publishing schedules table
CREATE TABLE publishing_schedules (
    id SERIAL PRIMARY KEY,
    content_id INTEGER NOT NULL REFERENCES contents(id),
    platform VARCHAR(50),
    scheduled_time TIMESTAMP WITH TIME ZONE,
    published_time TIMESTAMP WITH TIME ZONE,
    is_published BOOLEAN DEFAULT FALSE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    INDEX idx_content_id (content_id),
    INDEX idx_scheduled_time (scheduled_time),
    INDEX idx_platform (platform)
);

-- Trends table
CREATE TABLE trends (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    source VARCHAR(50),
    trend_score FLOAT,
    viral_score FLOAT,
    rank INTEGER,
    confidence FLOAT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    INDEX idx_source (source),
    INDEX idx_created_at (created_at)
);

-- A/B Tests table
CREATE TABLE ab_tests (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    variant_a JSONB,
    variant_b JSONB,
    winning_variant VARCHAR(1),
    status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
