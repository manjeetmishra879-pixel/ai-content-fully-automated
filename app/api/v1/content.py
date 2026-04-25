"""
Content generation endpoints — backed by real LLM engines (Ollama).
"""

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.engines import get_engine
from app.models.models import Post, Trend, User
from app.schemas import (
    ContentGenerationRequest,
    ContentGenerationResponse,
    TrendRequest,
    TrendResponse,
)

router = APIRouter(prefix="/content", tags=["content"])


def _generate_full(req: ContentGenerationRequest, db: Session) -> Dict[str, Any]:
    """Run the full LLM pipeline: script → hooks → captions → quality."""
    content = get_engine("content")
    hook = get_engine("hook")
    caption = get_engine("caption")
    quality = get_engine("quality")
    engagement = get_engine("engagement_prediction")

    trends_context: List[str] = []
    if req.trend_ids:
        trends = db.query(Trend).filter(Trend.id.in_(req.trend_ids)).all()
        trends_context = [t.title for t in trends if t.title]

    script_data = content(
        topic=req.topic,
        content_type=req.content_type,
        tone=req.tone or "energetic",
        language=req.language,
        platforms=req.platforms,
        hashtag_count=req.hashtag_count or 10,
        include_cta=bool(req.include_cta),
        trends=trends_context,
    )
    title = script_data.get("title") or req.topic
    script = script_data.get("script") or ""
    base_hashtags = script_data.get("hashtags") or []
    ctas = script_data.get("ctas") or []

    hooks_data = hook(topic=req.topic, count=5, language=req.language,
                       platform=req.platforms[0] if req.platforms else "instagram")
    hooks_raw = hooks_data.get("hooks", [])
    # Hook engine returns either list of strings or list of {text, score} dicts.
    hooks: List[str] = [
        h["text"] if isinstance(h, dict) else str(h)
        for h in hooks_raw
    ]

    cta = (ctas[0] if ctas else None) if req.include_cta else None
    captions = caption(
        script=script, platforms=req.platforms, hashtags=base_hashtags,
        cta=cta, language=req.language,
    )
    if not isinstance(captions, dict):
        captions = {}

    q = quality(script=script, hooks=hooks, hashtags=base_hashtags,
                ctas=ctas, captions=captions)
    qscore = float(q.get("score", 0.0))
    primary_platform = req.platforms[0] if req.platforms else "instagram"
    eng = engagement(script=script, hooks=hooks, hashtags=base_hashtags,
                     ctas=ctas, platform=primary_platform)
    virality = float(eng.get("virality_probability", 0.0))

    return {
        "title": title,
        "script": script,
        "hooks": hooks,
        "hashtags": base_hashtags[: (req.hashtag_count or 5)],
        "ctas": ctas[:5] or ["Follow for more!"],
        "captions": captions,
        "quality_score": qscore,
        "virality_potential": virality,
    }


@router.post("/generate", response_model=ContentGenerationResponse)
async def generate_content(
    request: ContentGenerationRequest,
    user_id: int = Depends(lambda: 1),
    db: Session = Depends(get_db),
) -> ContentGenerationResponse:
    """Generate AI-powered content with the LLM pipeline."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    data = _generate_full(request, db)

    primary_caption = next(iter(data["captions"].values()), data["script"])
    post = Post(
        user_id=user_id,
        title=data["title"][:500],
        script=data["script"],
        caption=primary_caption,
        hooks=data["hooks"],
        cta_text=(data["ctas"] or [""])[0][:500],
        category=request.tone or "general",
        content_type=request.content_type,
        language=request.language,
        platforms={p: {"caption": c} for p, c in data["captions"].items()},
        quality_score=data["quality_score"],
        engagement_prediction=data["virality_potential"],
        status="draft",
        extra_metadata={
            "hashtags": data["hashtags"],
            "ctas": data["ctas"],
            "tone": request.tone,
            "target_platforms": request.platforms,
            "generated_with_ai": True,
        },
    )
    db.add(post); db.commit(); db.refresh(post)

    return ContentGenerationResponse(
        id=post.id,
        script=data["script"],
        title=data["title"],
        hooks=data["hooks"],
        hashtags=data["hashtags"],
        ctas=data["ctas"],
        captions=data["captions"],
        quality_score=data["quality_score"],
        virality_potential=data["virality_potential"],
        generated_at=datetime.utcnow(),
    )


@router.post("/regenerate/{post_id}", response_model=ContentGenerationResponse)
async def regenerate_content(
    post_id: int,
    request: ContentGenerationRequest,
    user_id: int = Depends(lambda: 1),
    db: Session = Depends(get_db),
) -> ContentGenerationResponse:
    post = db.query(Post).filter(Post.id == post_id, Post.user_id == user_id).first()
    if not post:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found")

    data = _generate_full(request, db)
    primary_caption = next(iter(data["captions"].values()), data["script"])
    post.title = data["title"][:500]
    post.script = data["script"]
    post.caption = primary_caption
    post.hooks = data["hooks"]
    post.cta_text = (data["ctas"] or [""])[0][:500]
    post.platforms = {p: {"caption": c} for p, c in data["captions"].items()}
    post.quality_score = data["quality_score"]
    post.engagement_prediction = data["virality_potential"]
    meta = dict(post.extra_metadata or {})
    meta.update({"hashtags": data["hashtags"], "ctas": data["ctas"]})
    post.extra_metadata = meta
    db.commit(); db.refresh(post)

    return ContentGenerationResponse(
        id=post.id,
        script=data["script"],
        title=data["title"],
        hooks=data["hooks"],
        hashtags=data["hashtags"],
        ctas=data["ctas"],
        captions=data["captions"],
        quality_score=data["quality_score"],
        virality_potential=data["virality_potential"],
        generated_at=datetime.utcnow(),
    )


@router.post("/trends", response_model=List[TrendResponse])
async def get_trending_topics(
    request: TrendRequest,
    user_id: int = Depends(lambda: 1),
    db: Session = Depends(get_db),
) -> List[TrendResponse]:
    """Pull live trends (Google News + YouTube + Reddit + HN) and persist them."""
    trend_engine = get_engine("trend")
    result = trend_engine(platform=request.platform, language=request.language,
                           limit=request.limit, db=db, user_id=user_id)
    items = result.get("trends", [])
    return [
        TrendResponse(
            id=item.get("id") or 0,
            title=item.get("title", "")[:255],
            description=item.get("description", "") or "",
            growth_rate=float(item.get("growth_rate") or 0.0),
            saturation_level=item.get("saturation_level") or "medium",
            source=item.get("source") or "unknown",
            related_hashtags=item.get("related_hashtags") or [],
            recommendations=item.get("recommendations") or {},
        )
        for item in items
    ]


@router.post("/translate")
async def translate_text(
    text: str,
    target_language: str = "hindi",
    source_language: str = "english",
) -> Dict[str, Any]:
    engine = get_engine("translation")
    return engine(text=text, target_language=target_language,
                  source_language=source_language)


@router.post("/marketing/copy")
async def marketing_copy(
    product: str,
    audience: str = "general",
    objective: str = "engagement",
    tone: str = "persuasive",
) -> Dict[str, Any]:
    engine = get_engine("marketing")
    return engine(product=product, audience=audience, objective=objective, tone=tone)


@router.post("/engagement/train")
async def train_engagement_models(
    training_data: List[Dict[str, Any]],
    data_source: str = "real",
    user_id: int = Depends(lambda: 1),
) -> Dict[str, Any]:
    """Train ML models for engagement prediction using historical data"""
    if len(training_data) < 50:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Need at least 50 training samples"
        )

    engine = get_engine("engagement_prediction")
    results = engine.train_models(training_data, data_source)

    if "error" in results:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Training failed: {results['error']}"
        )

    return {
        "message": "Models trained successfully",
        "performance": results.get("performance", {}),
        "trained_metrics": results.get("trained_metrics", []),
        "total_samples": results.get("total_samples", 0),
        "data_source": data_source,
        "feature_count": results.get("feature_count", 0)
    }


@router.get("/engagement/models/info")
async def get_engagement_model_info() -> Dict[str, Any]:
    """Get information about trained engagement prediction models"""
    engine = get_engine("engagement_prediction")
    return engine.get_model_info()


@router.post("/engagement/collect-data")
async def collect_engagement_data(
    post_id: int,
    actual_metrics: Dict[str, Any],
    user_id: int = Depends(lambda: 1),
) -> Dict[str, Any]:
    """Collect real engagement data for future model retraining"""
    engine = get_engine("engagement_prediction")
    return engine.collect_real_engagement_data(post_id, actual_metrics)


@router.get("/engagement/data/stats")
async def get_engagement_data_stats() -> Dict[str, Any]:
    """Get statistics about collected real engagement data"""
    engine = get_engine("engagement_prediction")
    return engine.get_real_data_stats()


@router.post("/engagement/auto-fetch")
async def trigger_auto_fetch_engagement_data(
    user_id: int = None,
    hours_back: int = 24,
    background: bool = True,
) -> Dict[str, Any]:
    """Trigger automatic collection of engagement data from all platforms"""
    from app.tasks.analytics_tasks import auto_fetch_engagement_data

    if background:
        # Run in background via Celery
        task = auto_fetch_engagement_data.delay(user_id=user_id, hours_back=hours_back)
        return {
            "message": "Auto-fetch task started in background",
            "task_id": task.id,
            "user_id": user_id,
            "hours_back": hours_back,
            "status": "running"
        }
    else:
        # Run synchronously (for testing)
        result = auto_fetch_engagement_data(user_id=user_id, hours_back=hours_back)
        return {
            "message": "Auto-fetch completed",
            "result": result
        }


@router.post("/engagement/update-followers")
async def trigger_update_account_followers(
    user_id: int = None,
    background: bool = True,
) -> Dict[str, Any]:
    """Trigger update of follower counts across all platforms"""
    from app.tasks.analytics_tasks import update_account_followers

    if background:
        # Run in background via Celery
        task = update_account_followers.delay(user_id=user_id)
        return {
            "message": "Follower update task started in background",
            "task_id": task.id,
            "user_id": user_id,
            "status": "running"
        }
    else:
        # Run synchronously (for testing)
        result = update_account_followers(user_id=user_id)
        return {
            "message": "Follower update completed",
            "result": result
        }


@router.post("/engagement/retrain-model")
async def trigger_model_retraining(
    background: bool = True,
) -> Dict[str, Any]:
    """Trigger manual retraining of the engagement prediction model"""
    from app.tasks.analytics_tasks import retrain_engagement_model

    if background:
        # Run in background via Celery
        task = retrain_engagement_model.delay()
        return {
            "message": "Model retraining task started in background",
            "task_id": task.id,
            "status": "running"
        }
    else:
        # Run synchronously (for testing)
        result = retrain_engagement_model()
        return {
            "message": "Model retraining completed",
            "result": result
        }


@router.get("/engagement/monitoring")
async def get_engagement_monitoring_data() -> Dict[str, Any]:
    """Get monitoring data for the auto-fetch system"""
    from app.services.analytics_service import AnalyticsService
    from app.core.database import get_db
    from sqlalchemy.orm import Session

    db: Session = next(get_db())
    try:
        analytics_service = AnalyticsService(db)

        # Get data collection stats
        data_stats = analytics_service.get_real_data_stats()

        # Get recent task status (mock for now)
        recent_tasks = {
            "auto_fetch_last_run": "2024-01-15T06:00:00Z",
            "follower_update_last_run": "2024-01-15T04:00:00Z",
            "model_retrain_last_run": "2024-01-14T05:00:00Z",
            "tasks_today": 12,
            "successful_fetches_today": 8,
            "failed_fetches_today": 4
        }

        # Get API quota status (mock)
        api_quotas = {
            "youtube": {"used": 8500, "limit": 10000, "reset": "2024-01-16T00:00:00Z"},
            "instagram": {"used": 180, "limit": 200, "reset": "2024-01-15T12:00:00Z"},
            "tiktok": {"used": 85, "limit": 100, "reset": "2024-01-15T12:00:00Z"}
        }

        return {
            "data_collection": data_stats,
            "recent_activity": recent_tasks,
            "api_quotas": api_quotas,
            "system_health": "healthy"
        }

    finally:
        db.close()
