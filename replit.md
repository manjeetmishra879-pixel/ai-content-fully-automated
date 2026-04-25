# AI Content Automation Empire Platform

## Overview
FastAPI-based REST API for automated AI-powered content creation,
publishing, learning and analytics across social-media platforms. Hosts
**37 real engines** (LLM, trends, media, quality, learning, strategy,
distribution) backed by Ollama (Mistral) for local inference and direct
SDKs for each social network.

## Tech Stack
- **Language**: Python 3.11
- **Framework**: FastAPI + Uvicorn
- **ORM**: SQLAlchemy 2.0 (PostgreSQL via Replit DB)
- **LLM**: Ollama (Mistral 7B) at `127.0.0.1:8008`
- **Validation**: Pydantic 2 + pydantic-settings
- **Publishers**: tweepy (X), facebook-sdk (FB/IG via Graph), praw (Reddit),
  resumable upload to YouTube, native HTTPS for Telegram/LinkedIn.

## Project Structure
- `app/main.py` — FastAPI entry; CORS + request log middleware; seeds
  `User.id=1` for single-tenant dev mode on startup.
- `app/api/v1/` — Versioned routers:
  - `health.py`, `auth.py`, `analytics.py` (legacy)
  - `content.py` — full LLM pipeline (script → hooks → captions → quality)
  - `publish.py` — `/now`, `/schedule`, cancel, list schedules
  - `engines.py` — engine registry browser
  - `accounts.py` — register & rotate social accounts; shadowban check
  - `media.py` — TTS, image, video engine triggers
  - `learning.py` — A/B bandit, anti-duplication, hashtag learning,
    best-time, freshness, decay, skip analysis
  - `strategy.py` — buckets, series, platform psychology, comment-CTA,
    humanize, route, competitor
- `app/engines/` — All real engines, registered via `_bootstrap()`:
  - `llm/` — Ollama client + content/hook/caption/marketing/translation
  - `trends/`, `media/`, `quality/`, `learning/`, `strategy/`
  - `distribution/` — `platforms.py` (real SDK calls), `publisher_engine.py`,
    `scheduler.py`, `account_manager.py`, `human_mimicry.py`,
    `shadowban_detection.py`
- `app/models/models.py` — SQLAlchemy ORM (User, Account, Post, Schedule,
  Log, Analytics, Trend, Hashtag, Asset, …). Two FKs from `posts → users`
  (`user_id` + `reviewer_id`) handled with explicit `foreign_keys=`.
- `app/schemas/__init__.py` — Pydantic request/response schemas.

## Engine ↔ API Conventions
- Engines never crash — every external call (Ollama, social APIs) returns
  a uniform dict with `published`/`error` and falls back to a template
  when the LLM is unreachable.
- `OllamaClient.generate` raises `OllamaUnavailable` for both connection
  errors **and** HTTP 4xx/5xx (e.g. when Mistral isn't pulled yet); all
  text-LLM engines catch this and use deterministic templates.
- Per-platform credentials are stored in `Account.extra_metadata.credentials`
  (JSONB). `account_manager` exposes `action="credentials"` to fetch them
  and the publisher engine pipes them to the right SDK call.
- Hashtags live on `Post.extra_metadata["hashtags"]`; per-platform
  captions on `Post.platforms[platform]["caption"]`; publish-time URLs &
  IDs are written back into the same JSONB.

## Replit Setup
- **Workflows**:
  - `API Server` — `uvicorn app.main:app --host 0.0.0.0 --port 5000`
  - `Ollama Server` — `ollama serve` on `127.0.0.1:8008` with models in
    `.ollama_models/`
- **Mistral pull**: `/tmp/pull_loop.sh` retries `ollama pull mistral` up to
  60 attempts; until it completes, all LLM engines transparently use
  template fallbacks.
- **Database**: `DATABASE_URL` (Replit Postgres). Tables auto-create on
  startup; default user `id=1` is seeded.
- **CORS**: `*` (development).
- **Deployment target**: autoscale.

## Endpoints (curl-tested)
- `GET  /api/v1/engines/` — lists all 37 registered engines
- `POST /api/v1/content/generate` — full LLM pipeline; persists `Post`
- `POST /api/v1/publish/now` — invoke real platform SDKs
- `POST /api/v1/publish/schedule` — queue a `Schedule` row
- `POST /api/v1/accounts/` — register social account with credentials
- `GET  /api/v1/accounts/?platform=…` — list / `?strategy=` rotate
- `POST /api/v1/accounts/shadowban-check` — heuristic shadowban detection
- `GET  /api/v1/learning/freshness?topic=` / `/decay?…` / `/best-time?…`
- `POST /api/v1/learning/ab/create` → `/ab/{id}/pick` → `/ab/{id}/report`
- `POST /api/v1/strategy/{series,buckets,humanize,comment-cta,route,competitor}`

## Recent Fixes (this session)
1. Replaced placeholder engine modules with real implementations across
   all seven engine subpackages (37 engines total).
2. Wired publisher SDKs (`tweepy`, `praw`, Graph API, YouTube resumable
   upload) into `app/engines/distribution/platforms.py`.
3. Realigned `account_manager` to the actual `Account` schema
   (`username`, `extra_metadata.credentials`, `last_sync_at`).
4. Fixed `User.posts` ambiguous-FK error by pinning
   `foreign_keys="Post.user_id"`.
5. Made `OllamaClient` surface 4xx as `OllamaUnavailable` so every
   text-LLM engine falls back cleanly when Mistral is still pulling.
6. Rewrote `app/api/v1/learning.py` and `accounts.py` to match the actual
   engine action signatures (`recommend`, `ingest`, `stats`, `pick`,
   `report`, `winner`, `register`, `rotate`, `credentials`).
7. `content.py` pipeline aligned with real engine kwargs
   (`captions` is a dict per platform; engagement returns
   `virality_probability`).
8. `publish.py` `/now` now takes a single combined body (no more 422).
9. `app/main.py` seeds default `User.id=1` for single-tenant dev.

## Pending / Optional
- Mistral 7B (~4.4GB) is still completing pull in the background; once
  finished the LLM-backed paths replace the template fallbacks
  automatically.
- Real social credentials must be inserted via `POST /api/v1/accounts/`
  before any publish actually goes out.
