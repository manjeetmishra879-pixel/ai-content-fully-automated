"""
ViralRadarEngine — surfaces topics that are *rising fast* right now.

Maintains an in-memory rolling window of TrendEngine snapshots so it can
compute a velocity for each topic (current mentions vs previous snapshot).
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional

from app.engines.base import BaseEngine
from app.engines.trends.trend_engine import TrendEngine


class ViralRadarEngine(BaseEngine):
    name = "viral_radar"
    description = "Detect rising-fast trends in real time"

    def __init__(self) -> None:
        super().__init__()
        self.trend = TrendEngine()
        self._snapshots: Deque[Dict[str, Any]] = deque(maxlen=12)

    def run(
        self,
        *,
        category: Optional[str] = None,
        limit: int = 10,
        max_saturation: str = "medium",
    ) -> Dict[str, Any]:
        snapshot = self.trend.run(category=category, limit=40)
        topics = snapshot["topics"]
        self._snapshots.append({"ts": time.time(), "topics": {t["topic"]: t for t in topics}})

        # Velocity: change in mentions vs previous snapshot.
        velocities: List[Dict[str, Any]] = []
        prev = self._snapshots[-2]["topics"] if len(self._snapshots) >= 2 else {}
        for t in topics:
            prev_mentions = (prev.get(t["topic"]) or {}).get("mentions", 0)
            delta = t["mentions"] - prev_mentions
            velocity = (delta / max(prev_mentions, 1)) * 100 if prev_mentions else (delta * 25)
            t = dict(t, velocity=round(velocity, 2), mention_delta=delta)
            velocities.append(t)

        # Filter by saturation cap.
        order = {"low": 0, "medium": 1, "high": 2}
        cap = order.get(max_saturation, 1)
        eligible = [t for t in velocities if order.get(t["saturation_level"], 1) <= cap]

        rising = sorted(eligible, key=lambda x: (x["velocity"], x["viral_score"]), reverse=True)[:limit]
        return {
            "rising": rising,
            "snapshots_in_window": len(self._snapshots),
            "category": category,
        }
