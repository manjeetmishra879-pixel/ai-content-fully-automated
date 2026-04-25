"""
HumanMimicryEngine — adds realistic randomness to publishing actions
to reduce bot detection footprint.
"""

from __future__ import annotations

import datetime as dt
import random
from typing import Any, Dict, List, Optional

from app.engines.base import BaseEngine


class HumanMimicryEngine(BaseEngine):
    name = "human_mimicry"
    description = "Make publishing patterns look natural"

    def run(self, action: str = "delay", **kwargs: Any) -> Any:
        if action == "delay":
            return self.suggest_delay(**kwargs)
        if action == "shuffle_hashtags":
            return self.shuffle_hashtags(kwargs["hashtags"])
        if action == "skip_today":
            return self.maybe_skip(kwargs.get("publish_streak", 0))
        if action == "jitter_caption":
            return self.jitter_caption(kwargs["caption"])
        raise ValueError("unknown action")

    # ------------------------------------------------------------------
    def suggest_delay(self, *, base_seconds: int = 120,
                      jitter_pct: float = 0.4) -> Dict[str, Any]:
        jitter = base_seconds * jitter_pct
        delay = max(5, int(base_seconds + random.uniform(-jitter, jitter)))
        return {"delay_seconds": delay,
                "execute_at": (dt.datetime.utcnow()
                                + dt.timedelta(seconds=delay)).isoformat()}

    def shuffle_hashtags(self, hashtags: List[str]) -> List[str]:
        out = list(hashtags)
        random.shuffle(out)
        # Drop one tag at random sometimes — humans are sloppy.
        if len(out) > 6 and random.random() < 0.25:
            out.pop()
        return out

    def maybe_skip(self, publish_streak: int) -> Dict[str, Any]:
        # Real creators skip days. Skip probability rises with streak length.
        prob = min(0.35, 0.05 + 0.025 * publish_streak)
        skip = random.random() < prob
        return {"skip": skip, "streak": publish_streak,
                "skip_probability": round(prob, 3)}

    def jitter_caption(self, caption: str) -> str:
        if not caption or len(caption) < 30:
            return caption
        # Occasionally double-space, or add a small typo style emoji.
        flourishes = [" ✨", " 💛", " ⚡", " 🔥", "", "", ""]
        return caption + random.choice(flourishes)
