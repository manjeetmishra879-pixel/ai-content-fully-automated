"""
QualityEngine — scores a content package and recommends a publish gate.

Score components (out of 100):
  - hook_strength       (25)
  - script_structure    (20)
  - engagement_signals  (15)
  - hashtag_quality     (10)
  - cta_strength        (10)
  - readability         (10)
  - originality_signal  (10)

Decision thresholds:
  >= 75: publish
  60-74: review
  < 60 : regenerate
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.engines.base import BaseEngine
from app.engines.llm.hook_engine import HookEngine


POWER_WORDS = {
    "free", "secret", "instantly", "guaranteed", "proven", "exclusive",
    "limited", "today", "now", "new", "save", "stop", "warning", "shocking",
    "discover", "ultimate", "powerful", "easy", "fast",
}
EMOTION_WORDS = {
    "love", "hate", "fear", "joy", "angry", "sad", "happy", "excited",
    "amazing", "incredible", "unbelievable", "shocked", "surprised",
    "transform", "change", "win", "lose", "fail", "succeed",
}


class QualityEngine(BaseEngine):
    name = "quality"
    description = "Score content quality and decide publish gate"

    def __init__(self) -> None:
        super().__init__()
        # Reuse the hook scoring heuristic.
        self._hook_engine = None

    def _hook_score(self, hook: str) -> float:
        if self._hook_engine is None:
            try:
                self._hook_engine = HookEngine()
            except Exception:
                self._hook_engine = False
        if self._hook_engine and self._hook_engine is not False:
            return self._hook_engine._score(hook)
        return 60.0

    # ------------------------------------------------------------------
    def run(
        self,
        *,
        script: str,
        title: Optional[str] = None,
        hooks: Optional[List[str]] = None,
        hashtags: Optional[List[str]] = None,
        ctas: Optional[List[str]] = None,
        captions: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        script = (script or "").strip()
        words = script.split()

        # Hook strength: best-of hooks.
        hooks = hooks or []
        hook_scores = [self._hook_score(h) for h in hooks if isinstance(h, str)]
        hook_strength = max(hook_scores) if hook_scores else 50.0
        hook_pts = (hook_strength / 100.0) * 25

        # Structure: presence of hook → body → cta arc.
        structure_pts = 0
        if len(words) >= 30: structure_pts += 8
        if any(p in script.lower() for p in ["first", "second", "third", "1.", "2.", "3."]):
            structure_pts += 4
        if any(c in (script.lower() if script else "") for c in
               ["save", "follow", "share", "comment", "tag", "subscribe"]):
            structure_pts += 4
        if 60 <= len(words) <= 220:
            structure_pts += 4
        structure_pts = min(20, structure_pts)

        # Engagement signals: power & emotion words.
        lower = script.lower()
        power_hits = sum(1 for w in POWER_WORDS if w in lower)
        emo_hits = sum(1 for w in EMOTION_WORDS if w in lower)
        engagement_pts = min(15, power_hits * 1.5 + emo_hits * 1.0 + 2)

        # Hashtag quality: not too few, not too many, no duplicates.
        hashtags = hashtags or []
        ht_unique = len({h.lower() for h in hashtags})
        if 5 <= ht_unique <= 20:
            hashtag_pts = 10
        elif 3 <= ht_unique <= 30:
            hashtag_pts = 6
        else:
            hashtag_pts = 2

        # CTA strength.
        ctas = ctas or []
        cta_pts = min(10, len(ctas) * 3)

        # Readability: sentence length sweet spot.
        sentences = re.split(r"[.!?]+", script)
        avg_words = (sum(len(s.split()) for s in sentences if s.strip()) /
                     max(1, sum(1 for s in sentences if s.strip())))
        if 8 <= avg_words <= 18:
            readability_pts = 10
        elif 5 <= avg_words <= 25:
            readability_pts = 6
        else:
            readability_pts = 3

        # Originality: penalize obvious template phrases.
        cliches = ["here's why", "you won't believe", "in this video",
                   "guys today", "without further ado"]
        cliche_hits = sum(1 for c in cliches if c in lower)
        originality_pts = max(0, 10 - cliche_hits * 3)

        total = hook_pts + structure_pts + engagement_pts + hashtag_pts + cta_pts \
            + readability_pts + originality_pts
        total = round(min(100.0, total), 2)

        if total >= 75:
            decision, reason = "publish", "High-quality package, safe to ship."
        elif total >= 60:
            decision, reason = "review", "Acceptable but worth a human pass."
        else:
            decision, reason = "regenerate", "Below quality bar, regenerate."

        return {
            "score": total,
            "decision": decision,
            "reason": reason,
            "components": {
                "hook_strength": round(hook_pts, 2),
                "structure": round(structure_pts, 2),
                "engagement_signals": round(engagement_pts, 2),
                "hashtag_quality": round(hashtag_pts, 2),
                "cta_strength": round(cta_pts, 2),
                "readability": round(readability_pts, 2),
                "originality": round(originality_pts, 2),
            },
            "stats": {
                "word_count": len(words),
                "avg_sentence_words": round(avg_words, 2),
                "power_word_hits": power_hits,
                "emotion_word_hits": emo_hits,
                "hashtag_count": ht_unique,
            },
        }
