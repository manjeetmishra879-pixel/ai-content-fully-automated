"""
Learning loop endpoints — A/B testing, anti-duplication, hashtag learning,
best-time, freshness, decay, skip analysis.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body
from pydantic import BaseModel, Field

from app.engines import get_engine

router = APIRouter(prefix="/learning", tags=["learning"])


# ---------------------------------------------------------------------------
# A/B testing — Beta-Bandit
# ---------------------------------------------------------------------------
class ABCreateRequest(BaseModel):
    name: str
    variants: List[str]


@router.post("/ab/create")
async def ab_create(payload: ABCreateRequest) -> Dict[str, Any]:
    return get_engine("ab_testing")(action="create", **payload.dict())


@router.get("/ab/{test_id}/pick")
async def ab_pick(test_id: str) -> Dict[str, Any]:
    return get_engine("ab_testing")(action="pick", test_id=test_id)


class ABReportRequest(BaseModel):
    variant_id: str
    converted: bool = False


@router.post("/ab/{test_id}/report")
async def ab_report(test_id: str, payload: ABReportRequest) -> Dict[str, Any]:
    return get_engine("ab_testing")(action="report", test_id=test_id,
                                     variant_id=payload.variant_id,
                                     converted=payload.converted)


@router.post("/ab/{test_id}/winner")
async def ab_winner(test_id: str) -> Dict[str, Any]:
    return get_engine("ab_testing")(action="winner", test_id=test_id)


@router.get("/ab")
async def ab_list() -> Dict[str, Any]:
    return {"tests": get_engine("ab_testing")(action="list")}


# ---------------------------------------------------------------------------
# Anti-duplication
# ---------------------------------------------------------------------------
class DupCheckRequest(BaseModel):
    kind: str = Field("text", description="text|image|video")
    text: Optional[str] = None
    path: Optional[str] = None
    threshold: Optional[float] = None


@router.post("/duplicates/check")
async def dup_check(payload: DupCheckRequest) -> Dict[str, Any]:
    args: Dict[str, Any] = {"kind": payload.kind}
    if payload.kind == "text" and payload.text is not None:
        args["text"] = payload.text
    elif payload.kind in ("image", "video") and payload.path:
        args["path"] = payload.path
    if payload.threshold is not None:
        args["threshold"] = payload.threshold
    return get_engine("anti_duplication")(**args)


# ---------------------------------------------------------------------------
# Hashtag learning
# ---------------------------------------------------------------------------
class HashtagIngestRequest(BaseModel):
    records: List[Dict[str, Any]]


@router.post("/hashtags/ingest")
async def hashtag_ingest(payload: HashtagIngestRequest) -> Dict[str, Any]:
    return get_engine("hashtag_learning")(action="ingest", records=payload.records)


@router.get("/hashtags/recommend")
async def hashtag_recommend(topic: Optional[str] = None,
                             count: int = 12) -> Dict[str, Any]:
    return get_engine("hashtag_learning")(action="recommend", topic=topic, count=count)


@router.get("/hashtags/stats")
async def hashtag_stats() -> Dict[str, Any]:
    return get_engine("hashtag_learning")(action="stats")


# ---------------------------------------------------------------------------
# Best-time
# ---------------------------------------------------------------------------
@router.get("/best-time")
async def best_time(platform: str, top_k: int = 4) -> Dict[str, Any]:
    return get_engine("best_time")(action="best_times", platform=platform, top_k=top_k)


class BestTimeIngest(BaseModel):
    records: List[Dict[str, Any]]


@router.post("/best-time/ingest")
async def best_time_ingest(payload: BestTimeIngest) -> Dict[str, Any]:
    return get_engine("best_time")(action="ingest", records=payload.records)


# ---------------------------------------------------------------------------
# Skip analysis
# ---------------------------------------------------------------------------
class SkipRequest(BaseModel):
    retention_curve: List[float]
    duration_s: float = 30.0


@router.post("/skip-analysis")
async def skip_analysis(payload: SkipRequest) -> Dict[str, Any]:
    return get_engine("skip_analysis")(**payload.dict())


# ---------------------------------------------------------------------------
# Freshness & decay
# ---------------------------------------------------------------------------
@router.get("/freshness")
async def freshness(topic: str, cooldown_days: int = 7) -> Dict[str, Any]:
    return get_engine("content_freshness")(topic=topic, cooldown_days=cooldown_days)


@router.get("/decay")
async def decay(hours_since_publish: float,
                 initial_engagement: float = 1.0,
                 half_life_hours: float = 18.0) -> Dict[str, Any]:
    return get_engine("content_decay")(hours_since_publish=hours_since_publish,
                                        initial_engagement=initial_engagement,
                                        half_life_hours=half_life_hours)
