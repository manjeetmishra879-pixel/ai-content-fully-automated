"""
Publishing & scheduling endpoints — backed by real platform APIs.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.engines import get_engine
from app.models.models import Account, Post, Schedule
from app.schemas import (
    PublishRequest,
    PublishResponse,
    ScheduleRequest,
    ScheduleResponse,
)

router = APIRouter(prefix="/publish", tags=["publishing"])


class MediaPayload(BaseModel):
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    image_path: Optional[str] = None
    video_path: Optional[str] = None
    image_paths: Optional[List[str]] = None
    link_url: Optional[str] = None
    is_reel: bool = False
    subreddit: Optional[str] = None
    privacy: str = "public"


class PublishNowRequest(PublishRequest):
    media: Optional[MediaPayload] = None


@router.post("/now", response_model=PublishResponse)
async def publish_immediately(
    request: PublishNowRequest,
    user_id: int = Depends(lambda: 1),
    db: Session = Depends(get_db),
) -> PublishResponse:
    publisher = get_engine("publisher")
    result = publisher(
        db=db, user_id=user_id, post_id=request.post_id,
        platforms=request.platforms,
        media=(request.media.dict() if request.media else {}),
    )
    platforms_status = {r["platform"]: ("published" if r["published"] else f"failed: {r.get('error') or 'unknown'}")
                        for r in result["results"]}
    urls = {r["platform"]: r["url"] for r in result["results"] if r.get("url")}
    final_status = "published" if result["summary"]["successes"] else "failed"
    return PublishResponse(
        post_id=request.post_id,
        status=final_status,
        platforms_status=platforms_status,
        published_at=datetime.utcnow() if final_status == "published" else None,
        scheduled_for=None,
        urls=urls,
    )


@router.post("/schedule", response_model=ScheduleResponse)
async def schedule_post(
    request: ScheduleRequest,
    user_id: int = Depends(lambda: 1),
    db: Session = Depends(get_db),
) -> ScheduleResponse:
    post = db.query(Post).filter(Post.id == request.post_id, Post.user_id == user_id).first()
    if not post:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found")
    if request.scheduled_time <= datetime.utcnow().replace(tzinfo=request.scheduled_time.tzinfo):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Scheduled time must be in the future")

    scheduler = get_engine("scheduler")
    sched = scheduler(action="schedule", db=db, user_id=user_id,
                       post_id=request.post_id, platform=request.platform,
                       scheduled_at=request.scheduled_time, jitter_seconds=0)
    if post.status == "draft":
        post.status = "scheduled"
        db.commit()

    return ScheduleResponse(
        id=sched["id"],
        post_id=sched["post_id"],
        platform=sched["platform"],
        scheduled_time=request.scheduled_time,
        status=sched["status"],
        created_at=datetime.utcnow(),
    )


@router.post("/{post_id}/cancel")
async def cancel_schedule(
    post_id: int,
    schedule_id: int,
    user_id: int = Depends(lambda: 1),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    schedule = (db.query(Schedule)
                .filter(Schedule.id == schedule_id, Schedule.user_id == user_id,
                        Schedule.post_id == post_id).first())
    if not schedule:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Schedule not found")
    if schedule.status == "published":
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                             "Cannot cancel already-published content")

    scheduler = get_engine("scheduler")
    scheduler(action="cancel", db=db, schedule_id=schedule_id)
    return {"message": "Schedule cancelled", "schedule_id": schedule_id,
            "cancelled_at": datetime.utcnow()}


@router.get("/{post_id}/schedules")
async def get_post_schedules(
    post_id: int,
    user_id: int = Depends(lambda: 1),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    post = db.query(Post).filter(Post.id == post_id, Post.user_id == user_id).first()
    if not post:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found")
    schedules = db.query(Schedule).filter(Schedule.post_id == post_id).all()
    return {
        "post_id": post_id,
        "schedules": [
            {"id": s.id, "platform": s.platform,
             "scheduled_time": s.scheduled_time, "status": s.status,
             "created_at": s.created_at}
            for s in schedules
        ],
    }
