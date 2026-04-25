"""
Timing-related learning engines:

  - BestTimeEngine: learns best publish times per platform from past performance.
  - SkipAnalysisEngine: detects the moment viewers skip a video.
  - ContentFreshnessEngine: tracks how stale a topic is and recommends rotation.
  - ContentDecayEngine: models how performance decays over time.
"""

from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict
from typing import Any, Dict, List, Optional

from app.engines.base import BaseEngine


class BestTimeEngine(BaseEngine):
    name = "best_time"
    description = "Learn best publish time-windows per platform"

    DEFAULT_TIMES = {
        "instagram": ["09:00", "12:00", "18:00", "21:00"],
        "tiktok":    ["07:00", "12:00", "19:00", "22:00"],
        "youtube":   ["14:00", "16:00", "20:00"],
        "youtube_shorts": ["12:00", "17:00", "21:00"],
        "facebook":  ["09:00", "13:00", "20:00"],
        "x":         ["08:00", "12:00", "17:00", "22:00"],
        "linkedin":  ["08:00", "12:00", "17:00"],
        "telegram":  ["10:00", "16:00", "20:00"],
    }

    def __init__(self) -> None:
        super().__init__()
        # platform -> hour -> list[engagement]
        self._stats: Dict[str, Dict[int, List[float]]] = defaultdict(lambda: defaultdict(list))

    def run(self, action: str = "best_times", **kwargs: Any) -> Any:
        if action == "ingest":
            return self.ingest(kwargs["records"])
        return self.best_times(kwargs.get("platform", "instagram"),
                                top_k=int(kwargs.get("top_k", 4)))

    def ingest(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Each record: {platform, published_at: ISO, engagement: float}"""
        n = 0
        for r in records:
            try:
                ts = dt.datetime.fromisoformat(str(r["published_at"]).replace("Z", "+00:00"))
            except Exception:
                continue
            self._stats[r["platform"]][ts.hour].append(float(r.get("engagement") or 0))
            n += 1
        return {"ingested": n}

    def best_times(self, platform: str, top_k: int = 4) -> Dict[str, Any]:
        bucket = self._stats.get(platform)
        if not bucket:
            return {"platform": platform, "times": self.DEFAULT_TIMES.get(
                platform, ["09:00", "13:00", "20:00"]), "source": "default"}
        ranked = sorted(
            ((hour, sum(vals) / len(vals), len(vals))
             for hour, vals in bucket.items() if vals),
            key=lambda x: x[1], reverse=True,
        )
        times = [f"{h:02d}:00" for h, _, _ in ranked[:top_k]]
        return {"platform": platform, "times": times, "source": "learned",
                "details": [{"hour": f"{h:02d}:00", "avg_engagement": round(e, 3),
                             "samples": n} for h, e, n in ranked[:top_k]]}


class SkipAnalysisEngine(BaseEngine):
    name = "skip_analysis"
    description = "Locate the moment viewers drop off"

    def run(self, *, retention_curve: List[float],
            duration_s: float = 30.0) -> Dict[str, Any]:
        if not retention_curve or len(retention_curve) < 2:
            return {"insufficient_data": True}
        # retention_curve: list of remaining-viewer ratios from 0..1 at evenly spaced points.
        per_point = duration_s / (len(retention_curve) - 1)
        biggest_drop = 0.0
        drop_at = 0.0
        for i in range(1, len(retention_curve)):
            drop = retention_curve[i - 1] - retention_curve[i]
            if drop > biggest_drop:
                biggest_drop, drop_at = drop, i * per_point
        # Average completion = mean of curve.
        avg_completion = sum(retention_curve) / len(retention_curve)
        # 50%-skip point.
        half_at: Optional[float] = None
        for i, v in enumerate(retention_curve):
            if v <= 0.5:
                half_at = i * per_point
                break
        return {
            "duration_s": duration_s,
            "average_completion": round(avg_completion, 4),
            "biggest_drop": {"at_s": round(drop_at, 2),
                             "magnitude": round(biggest_drop, 4)},
            "fifty_percent_skip_at_s": round(half_at, 2) if half_at is not None else None,
            "recommendation": (
                "Rework hook + first 3 seconds." if drop_at <= 4
                else "Tighten the mid-section near the drop point."
                     if drop_at <= duration_s * 0.7
                     else "Strengthen the closing payoff."
            ),
        }


class ContentFreshnessEngine(BaseEngine):
    name = "content_freshness"
    description = "Track topic recency and recommend rotation"

    def __init__(self) -> None:
        super().__init__()
        self._last_used: Dict[str, dt.datetime] = {}

    def mark_used(self, topic: str) -> None:
        self._last_used[topic.lower().strip()] = dt.datetime.utcnow()

    def run(self, *, topic: str, cooldown_days: int = 7) -> Dict[str, Any]:
        key = topic.lower().strip()
        now = dt.datetime.utcnow()
        last = self._last_used.get(key)
        if not last:
            return {"topic": topic, "fresh": True, "days_since": None,
                    "recommendation": "OK to publish"}
        days = (now - last).days
        fresh = days >= cooldown_days
        return {"topic": topic, "fresh": fresh, "days_since": days,
                "cooldown_days": cooldown_days,
                "recommendation": "OK to publish" if fresh
                                  else f"Wait {cooldown_days - days} more days"}


class ContentDecayEngine(BaseEngine):
    name = "content_decay"
    description = "Model post-publish engagement decay"

    def run(self, *, hours_since_publish: float,
            initial_engagement: float = 1.0,
            half_life_hours: float = 18.0) -> Dict[str, Any]:
        """Exponential decay model: e(t) = e0 * 0.5^(t / half_life)."""
        decay_factor = 0.5 ** (max(0.0, hours_since_publish) / max(1e-3, half_life_hours))
        current = initial_engagement * decay_factor
        return {
            "hours_since_publish": hours_since_publish,
            "half_life_hours": half_life_hours,
            "current_engagement_estimate": round(current, 6),
            "decay_factor": round(decay_factor, 6),
            "recommendation": (
                "Boost or repost" if decay_factor < 0.25 else
                "Engage in comments to extend reach" if decay_factor < 0.5 else
                "Still gaining — leave it"
            ),
        }
