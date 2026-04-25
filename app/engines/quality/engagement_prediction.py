"""
EngagementPredictionEngine — predicts likely watch-through, like rate
and share probability for a content package.

Uses signal-weighted heuristic; can be retrained later from actual
post-performance data via app/engines/learning/skip_analysis.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional

from app.engines.base import BaseEngine
from app.engines.quality.quality_engine import QualityEngine


PLATFORM_BASELINES = {
    # (avg_completion, avg_like_rate, avg_share_rate)
    "instagram": (0.55, 0.05, 0.012),
    "tiktok": (0.70, 0.08, 0.020),
    "youtube_shorts": (0.65, 0.04, 0.010),
    "youtube": (0.40, 0.03, 0.008),
    "facebook": (0.35, 0.03, 0.010),
    "x": (0.45, 0.02, 0.015),
    "linkedin": (0.50, 0.025, 0.012),
}


class EngagementPredictionEngine(BaseEngine):
    name = "engagement_prediction"
    description = "Predict watch-through, like and share probabilities"

    def __init__(self) -> None:
        super().__init__()
        self.quality = QualityEngine()

    def run(
        self,
        *,
        script: str,
        hooks: Optional[List[str]] = None,
        hashtags: Optional[List[str]] = None,
        ctas: Optional[List[str]] = None,
        platform: str = "instagram",
        duration_s: float = 30.0,
    ) -> Dict[str, Any]:
        q = self.quality(
            script=script, hooks=hooks, hashtags=hashtags, ctas=ctas,
        )
        score = q["score"]
        comp = q["components"]

        base_completion, base_like, base_share = PLATFORM_BASELINES.get(
            platform, PLATFORM_BASELINES["instagram"]
        )

        # Boost completion with hook strength and right duration.
        hook_factor = comp["hook_strength"] / 25.0
        duration_factor = 1.0
        if platform in ("tiktok", "instagram", "youtube_shorts"):
            # Sweet spot 18–35s for most short-form.
            duration_factor = 1.1 - (abs(duration_s - 26) / 60.0)
        completion = max(0.05, min(0.95, base_completion * (0.8 + hook_factor * 0.4) * duration_factor))

        # Like rate scales with engagement+structure.
        like_rate = base_like * (0.6 + (score / 200.0))
        like_rate = max(0.005, min(0.25, like_rate))

        # Share rate scales with originality + emotion words.
        share_rate = base_share * (0.6 + (comp["originality"] / 10.0) * 0.5
                                   + (comp["engagement_signals"] / 15.0) * 0.5)
        share_rate = max(0.001, min(0.10, share_rate))

        # Crude virality probability.
        virality = round(100.0 * (0.4 * completion + 0.4 * like_rate * 5 + 0.2 * share_rate * 20), 2)
        virality = float(min(99.0, virality))

        return {
            "platform": platform,
            "predicted_completion_rate": round(completion, 4),
            "predicted_like_rate": round(like_rate, 4),
            "predicted_share_rate": round(share_rate, 4),
            "virality_probability": virality,
            "expected_watch_seconds": round(duration_s * completion, 2),
            "quality_score": score,
            "notes": "Estimates use platform baselines and quality signals; "
                     "feed back actual analytics to improve accuracy.",
        }
