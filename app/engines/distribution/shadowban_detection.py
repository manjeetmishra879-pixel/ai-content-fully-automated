"""
ShadowbanDetectionEngine — heuristic detection of shadowban based on
post-level metric anomalies relative to baseline.
"""

from __future__ import annotations

from statistics import mean, pstdev
from typing import Any, Dict, List, Optional

from app.engines.base import BaseEngine


class ShadowbanDetectionEngine(BaseEngine):
    name = "shadowban_detection"
    description = "Detect likely shadowban from analytics drops"

    def run(self, *, recent_metrics: List[Dict[str, Any]],
            baseline_metrics: List[Dict[str, Any]],
            metric: str = "impressions") -> Dict[str, Any]:
        recent = [float(r.get(metric) or 0) for r in recent_metrics]
        baseline = [float(r.get(metric) or 0) for r in baseline_metrics]
        if len(recent) < 3 or len(baseline) < 5:
            return {"verdict": "insufficient_data",
                    "reason": "Need >=3 recent and >=5 baseline samples"}
        b_mean = mean(baseline)
        b_std = pstdev(baseline) or 1.0
        r_mean = mean(recent)
        z = (r_mean - b_mean) / b_std
        drop_pct = (b_mean - r_mean) / b_mean * 100 if b_mean else 0
        verdict = "ok"
        confidence = 0.0
        if drop_pct > 60 and z < -2.0:
            verdict, confidence = "likely_shadowban", min(0.95, abs(z) / 4.0)
        elif drop_pct > 35 and z < -1.0:
            verdict, confidence = "possible_throttle", min(0.7, abs(z) / 3.0)
        return {
            "verdict": verdict,
            "metric": metric,
            "drop_pct": round(drop_pct, 2),
            "z_score": round(z, 2),
            "confidence": round(confidence, 2),
            "recommendation": (
                "Pause posting 48h, change hashtag set, vary post times."
                if verdict == "likely_shadowban" else
                "Reduce repetitive hashtags and avoid identical captions."
                if verdict == "possible_throttle" else
                "No anomaly detected."
            ),
        }
