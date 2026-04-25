"""
TrendEngine — aggregates trending topics across sources, scores them
for virality and freshness, then returns a ranked list.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional

from app.engines.base import BaseEngine
from app.engines.trends.sources import (
    fetch_google_news,
    fetch_hackernews,
    fetch_reddit,
    fetch_youtube_trending,
)


STOPWORDS = set("""
the a an and or but if then so of to in on for at by from with as is are was were be been being
this that these those it its it's i you he she we they them us our your my his her their what when
where who whom how why which while can could should would will may might just about over into out up
""".split())


class TrendEngine(BaseEngine):
    name = "trend"
    description = "Aggregate, score and rank trending topics from multiple sources"

    def run(
        self,
        *,
        keyword: Optional[str] = None,
        category: Optional[str] = None,
        platforms: Optional[List[str]] = None,
        limit: int = 20,
        sources: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        sources = sources or ["google_news", "youtube", "reddit", "hackernews"]
        items: List[Dict[str, Any]] = []

        if "google_news" in sources:
            items += fetch_google_news(query=keyword, limit=30)
        if "youtube" in sources:
            items += fetch_youtube_trending(limit=30)
        if "reddit" in sources:
            sub = self._category_to_subreddit(category) if category else "popular"
            items += fetch_reddit(subreddit=sub, limit=30)
        if "hackernews" in sources:
            items += fetch_hackernews(limit=20)

        # Filter by keyword if provided.
        if keyword:
            kw = keyword.lower()
            items = [i for i in items if kw in (i.get("title") or "").lower()] or items

        # Build topic clusters from token frequency across titles.
        topics = self._cluster(items)
        # Score & rank.
        ranked = sorted(
            (self._score_topic(t, items) for t in topics),
            key=lambda x: x["viral_score"],
            reverse=True,
        )[:limit]

        return {
            "keyword": keyword,
            "category": category,
            "sources_used": sources,
            "raw_count": len(items),
            "topics": ranked,
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _category_to_subreddit(category: str) -> str:
        mapping = {
            "tech": "technology",
            "business": "business",
            "finance": "personalfinance",
            "fitness": "Fitness",
            "motivation": "GetMotivated",
            "education": "todayilearned",
            "entertainment": "entertainment",
            "news": "worldnews",
            "gaming": "gaming",
        }
        return mapping.get(category.lower(), "popular")

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        words = re.findall(r"[A-Za-z][A-Za-z'-]{2,}", (text or "").lower())
        return [w for w in words if w not in STOPWORDS]

    def _cluster(self, items: List[Dict[str, Any]]) -> List[str]:
        counter: Counter = Counter()
        for item in items:
            counter.update(self._tokenize(item.get("title", "")))
        # Take the most common tokens as topic seeds.
        return [w for w, _ in counter.most_common(40)]

    def _score_topic(self, topic: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        related = [i for i in items if topic in (i.get("title") or "").lower()]
        mentions = len(related)
        sources = {i.get("source") for i in related}
        engagement = sum(int(i.get("score", 0) or 0) + int(i.get("comments", 0) or 0)
                         for i in related)
        # Score: log-scaled mentions × source diversity × engagement bonus.
        viral = (
            math.log1p(mentions) * 25
            + len(sources) * 10
            + math.log1p(engagement) * 6
        )
        viral = round(min(99.0, viral), 2)

        # Saturation: more sources covering it = lower freshness.
        saturation = "low" if mentions <= 2 else "medium" if mentions <= 5 else "high"
        # Growth approximation: weight HN+Reddit recent engagement
        growth_rate = round(1.0 + math.log1p(engagement) / 4.0, 2)

        sample_titles = [i.get("title", "") for i in related[:3]]
        hashtags = [f"#{topic}", f"#{topic}trend", "#viral", "#fyp"]
        return {
            "topic": topic,
            "mentions": mentions,
            "sources": sorted(s for s in sources if s),
            "engagement": engagement,
            "viral_score": viral,
            "growth_rate": growth_rate,
            "saturation_level": saturation,
            "sample_titles": sample_titles,
            "related_hashtags": hashtags,
        }
