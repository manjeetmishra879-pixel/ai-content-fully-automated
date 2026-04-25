"""
HashtagLearningEngine — learns which hashtags drive impressions/engagement
from the analytics records and recommends the next batch to use.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.engines.base import BaseEngine


class HashtagLearningEngine(BaseEngine):
    name = "hashtag_learning"
    description = "Learn winning hashtags and recommend optimal sets"

    def __init__(self) -> None:
        super().__init__()
        # tag -> dict(uses, impressions, engagement)
        self._stats: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"uses": 0, "impressions": 0.0, "engagement": 0.0}
        )

    def run(
        self,
        action: str = "recommend",
        **kwargs: Any,
    ) -> Any:
        if action == "ingest":
            return self.ingest(kwargs["records"])
        if action == "recommend":
            return self.recommend(
                seed_topic=kwargs.get("topic"),
                desired=int(kwargs.get("count", 12)),
                niche_pool=kwargs.get("niche_pool"),
            )
        if action == "stats":
            return self.snapshot()
        raise ValueError("action must be ingest|recommend|stats")

    # ------------------------------------------------------------------
    def ingest(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Each record: {hashtags: [...], impressions: int, engagement: float}"""
        n = 0
        for r in records:
            tags = [t.lstrip("#").lower() for t in (r.get("hashtags") or [])]
            impressions = float(r.get("impressions") or 0)
            engagement = float(r.get("engagement") or 0)
            for t in tags:
                if not t:
                    continue
                s = self._stats[t]
                s["uses"] += 1
                s["impressions"] += impressions
                s["engagement"] += engagement
                n += 1
        return {"ingested": n, "unique_tags": len(self._stats)}

    def recommend(
        self,
        *,
        seed_topic: Optional[str] = None,
        desired: int = 12,
        niche_pool: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        # Compose pool: known winners + niche extras + seed topic.
        candidates: Dict[str, float] = {}
        for tag, s in self._stats.items():
            uses = max(1, s["uses"])
            ipu = s["impressions"] / uses
            epu = s["engagement"] / uses
            score = (ipu * 0.4) + (epu * 60.0) + min(uses, 20) * 0.5
            candidates[tag] = score

        # Add seeded extras if we don't have enough learned tags.
        for extra in (niche_pool or []):
            t = extra.lstrip("#").lower()
            candidates.setdefault(t, 5.0)
        if seed_topic:
            seed = seed_topic.lower().replace(" ", "")
            candidates.setdefault(seed, 8.0)
            for token in seed_topic.lower().split():
                candidates.setdefault(token, 4.0)

        # Mix: 50% top-engagement winners, 30% mid-tier, 20% long-tail / fresh.
        ranked = sorted(candidates.items(), key=lambda kv: kv[1], reverse=True)
        top = [t for t, _ in ranked[: max(1, desired // 2)]]
        mid_start = max(1, len(ranked) // 3)
        mid = [t for t, _ in ranked[mid_start: mid_start + max(1, desired // 3)]]
        tail = [t for t, _ in ranked[-max(1, desired // 5):]]
        merged: List[str] = []
        for t in top + mid + tail:
            if t not in merged:
                merged.append(f"#{t}")
            if len(merged) >= desired:
                break
        return {"recommended": merged[:desired], "candidates": len(candidates)}

    def snapshot(self) -> Dict[str, Any]:
        ranked = sorted(
            ((t, s["uses"], s["impressions"], s["engagement"])
             for t, s in self._stats.items()),
            key=lambda x: x[3], reverse=True,
        )[:50]
        return {"top_50": [{"tag": f"#{t}", "uses": int(u),
                            "impressions": imp, "engagement": eng}
                           for t, u, imp, eng in ranked]}
