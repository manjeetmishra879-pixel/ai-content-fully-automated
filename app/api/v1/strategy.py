"""
Strategy endpoints — content buckets, series, platform psychology,
comment CTA, humanized rewrite, category routing, competitor analysis.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body
from pydantic import BaseModel

from app.engines import get_engine

router = APIRouter(prefix="/strategy", tags=["strategy"])


class BucketsRequest(BaseModel):
    topic: str
    mix_size: int = 8


@router.post("/buckets")
async def buckets(payload: BucketsRequest) -> Dict[str, Any]:
    return get_engine("content_buckets")(**payload.dict())


class SeriesRequest(BaseModel):
    topic: str
    episodes: int = 7
    platform: str = "instagram"
    tone: str = "energetic"


@router.post("/series")
async def build_series(payload: SeriesRequest) -> Dict[str, Any]:
    return get_engine("series_builder")(**payload.dict())


@router.get("/platform-psychology")
async def platform_psychology(platform: str) -> Dict[str, Any]:
    return get_engine("platform_psychology")(platform=platform)


class CommentCTARequest(BaseModel):
    topic: str
    platform: str = "instagram"
    count: int = 5


@router.post("/comment-cta")
async def comment_cta(payload: CommentCTARequest) -> Dict[str, Any]:
    return get_engine("comment_cta")(**payload.dict())


class HumanizeRequest(BaseModel):
    text: str
    voice: str = "casual & confident"


@router.post("/humanize")
async def humanize(payload: HumanizeRequest) -> Dict[str, Any]:
    return get_engine("humanized_content")(**payload.dict())


class RouteRequest(BaseModel):
    topic: str
    available_categories: Optional[List[str]] = None


@router.post("/route")
async def route_category(payload: RouteRequest) -> Dict[str, Any]:
    return get_engine("category_router")(**payload.dict())


class CompetitorRequest(BaseModel):
    niche: str
    region: str = "global"
    timeframe: str = "last 7 days"


@router.post("/competitor")
async def competitor(payload: CompetitorRequest) -> Dict[str, Any]:
    return get_engine("competitor")(**payload.dict())
