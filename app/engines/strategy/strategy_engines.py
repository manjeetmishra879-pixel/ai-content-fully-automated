"""
Strategy engines:

  - ContentBucketsEngine: classifies a topic into a content bucket and
    returns a balanced 4-bucket mix (educate / entertain / inspire / sell).
  - SeriesBuilderEngine: turns a topic into a multi-episode series plan.
  - PlatformPsychologyEngine: per-platform behavioural rules for ranking
    and audience expectations.
  - CommentCTAEngine: generates seed comments and per-platform CTAs.
  - HumanizedContentEngine: rewrites copy to feel natural, not AI-generated.
  - CategoryRouterEngine: routes a topic to the right account/category.
  - CompetitorEngine: returns a concise competitor analysis prompt result.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.engines.base import BaseEngine
from app.engines.llm.ollama_client import OllamaUnavailable, get_ollama


CATEGORY_KEYWORDS = {
    "motivation": {"motivation", "mindset", "discipline", "success", "grit", "habit"},
    "business":   {"business", "startup", "founder", "marketing", "sales", "revenue"},
    "finance":    {"money", "invest", "stocks", "crypto", "wealth", "save", "tax"},
    "fitness":    {"workout", "fitness", "gym", "diet", "muscle", "abs", "weight"},
    "education":  {"learn", "study", "tutorial", "lesson", "explained", "guide"},
    "entertainment": {"funny", "meme", "comedy", "story", "drama"},
    "tech":       {"ai", "tech", "code", "software", "app", "developer", "gadget"},
    "news":       {"news", "breaking", "today", "update", "latest"},
    "religion":   {"god", "faith", "verse", "prayer", "spiritual"},
    "lifestyle":  {"travel", "food", "fashion", "beauty", "vlog"},
}

BUCKETS = ["educate", "entertain", "inspire", "sell"]


class ContentBucketsEngine(BaseEngine):
    name = "content_buckets"
    description = "Classify topic into a bucket and return a balanced mix"

    def run(self, *, topic: str, mix_size: int = 8) -> Dict[str, Any]:
        bucket = self._classify(topic)
        # Balanced 60/20/15/5 split toward the dominant bucket.
        weights = {"educate": 30, "entertain": 25, "inspire": 25, "sell": 20}
        weights[bucket] += 15
        norm = sum(weights.values())
        plan = []
        for b, w in weights.items():
            count = max(0, round(mix_size * w / norm))
            for i in range(count):
                plan.append({"bucket": b, "slot": i + 1})
        return {"primary_bucket": bucket, "mix": plan[:mix_size]}

    @staticmethod
    def _classify(topic: str) -> str:
        t = topic.lower()
        if any(w in t for w in ["how to", "guide", "tutorial", "explained", "tips"]):
            return "educate"
        if any(w in t for w in ["funny", "meme", "fail", "story"]):
            return "entertain"
        if any(w in t for w in ["why", "buy", "deal", "offer", "free", "limited"]):
            return "sell"
        return "inspire"


class SeriesBuilderEngine(BaseEngine):
    name = "series_builder"
    description = "Plan a multi-episode content series"

    def __init__(self) -> None:
        super().__init__()
        self.ollama = get_ollama()

    def run(self, *, topic: str, episodes: int = 7,
            platform: str = "instagram",
            tone: str = "energetic") -> Dict[str, Any]:
        prompt = (
            f"Design a {episodes}-episode short-form series on: {topic}. "
            f"Platform: {platform}. Tone: {tone}. "
            "For each episode return title, hook, learning_outcome, and a teaser for the NEXT episode. "
            'Return ONLY JSON: {"series_title": "...", "episodes": [{...}]}.'
        )
        try:
            data = self.ollama.generate_json(prompt, temperature=0.7, max_tokens=1200)
            if data.get("episodes"):
                return data
        except OllamaUnavailable:
            pass
        return self._template(topic, episodes)

    @staticmethod
    def _template(topic: str, episodes: int) -> Dict[str, Any]:
        return {
            "series_title": f"{topic.title()} — the {episodes}-part series",
            "episodes": [
                {
                    "episode": i,
                    "title": f"{topic} — part {i}",
                    "hook": f"Part {i}: the thing nobody told you about {topic}.",
                    "learning_outcome": f"Viewer learns one new angle on {topic}.",
                    "next_teaser": f"Tomorrow: the surprising twist in part {i + 1}." if i < episodes else None,
                } for i in range(1, episodes + 1)
            ],
        }


class PlatformPsychologyEngine(BaseEngine):
    name = "platform_psychology"
    description = "Per-platform behavioural rules and audience expectations"

    RULES = {
        "instagram": {
            "audience_mood": "scroll-and-save, lifestyle aspirational",
            "winning_formats": ["reel", "carousel", "story"],
            "ranking_signals": ["watch_time", "saves", "shares", "comments"],
            "do": ["High-contrast cover frame", "Save-worthy info", "Strong first 1.5s"],
            "dont": ["Long intros", "Watermarked TikTok content"],
        },
        "tiktok": {
            "audience_mood": "fast-paced, raw, trend-driven",
            "winning_formats": ["short_video", "duet", "stitch"],
            "ranking_signals": ["completion", "rewatch", "shares", "comments"],
            "do": ["Trending audio", "Pattern interrupt", "Loopable ending"],
            "dont": ["Polished ad-style edits", "External logos"],
        },
        "youtube_shorts": {
            "audience_mood": "binge mobile",
            "winning_formats": ["short", "clipped highlight"],
            "ranking_signals": ["completion", "likes_per_view"],
            "do": ["Hook within 1s", "Loopable", "Vertical 9:16"],
            "dont": ["Slow intro card"],
        },
        "youtube": {
            "audience_mood": "intentional, story-driven",
            "winning_formats": ["long_form", "video_essay", "tutorial"],
            "ranking_signals": ["AVD", "CTR", "session"],
            "do": ["Strong thumbnail", "Promise + payoff", "Chapters"],
            "dont": ["Misleading thumbnail", "Long ramps"],
        },
        "facebook": {
            "audience_mood": "community + nostalgia",
            "winning_formats": ["video", "story", "post"],
            "ranking_signals": ["meaningful_comments", "shares"],
            "do": ["Conversation starters"],
            "dont": ["Outbound links in body"],
        },
        "x": {
            "audience_mood": "wit + commentary",
            "winning_formats": ["thread", "single_quote", "image_quote"],
            "ranking_signals": ["replies", "bookmarks", "reposts"],
            "do": ["Sharp 1-line takes"],
            "dont": ["Long preambles", "External links in main tweet"],
        },
        "linkedin": {
            "audience_mood": "professional growth + insights",
            "winning_formats": ["text_post", "carousel", "video"],
            "ranking_signals": ["dwell_time", "comments", "reposts"],
            "do": ["First 2 lines = full hook", "Story → insight"],
            "dont": ["Hashtag spam"],
        },
        "telegram": {
            "audience_mood": "broadcast, fan club",
            "winning_formats": ["channel_post", "voice", "image"],
            "ranking_signals": ["views", "forwards", "reactions"],
            "do": ["Bold opener", "Single CTA"],
            "dont": ["Walls of text"],
        },
    }

    def run(self, *, platform: str) -> Dict[str, Any]:
        return {"platform": platform,
                "rules": self.RULES.get(platform, self.RULES["instagram"])}


class CommentCTAEngine(BaseEngine):
    name = "comment_cta"
    description = "Generate seed comments and per-platform CTAs"

    def __init__(self) -> None:
        super().__init__()
        self.ollama = get_ollama()

    def run(self, *, topic: str, platform: str = "instagram",
            count: int = 5) -> Dict[str, Any]:
        prompt = (
            f"Generate {count} seed comments and {count} CTAs for a {platform} post about: {topic}. "
            'Return ONLY JSON: {"seed_comments": ["..."], "ctas": ["..."]}.'
        )
        try:
            data = self.ollama.generate_json(prompt, temperature=0.7)
            if data.get("seed_comments") and data.get("ctas"):
                return data
        except OllamaUnavailable:
            pass
        return {
            "seed_comments": [
                f"This hit different. Anyone else feel called out by {topic}?",
                f"Saving this. The part about {topic} is gold.",
                f"What's your #1 tip for {topic}?",
                f"Sharing this with my friend who needs to hear it 💛",
                f"Plot twist nobody saw coming about {topic}.",
            ][:count],
            "ctas": [
                "Save this for later 💾",
                "Tag a friend who needs this",
                "Drop a 🔥 if this helped",
                "Comment your take below ⬇",
                "Follow for daily drops",
            ][:count],
        }


class HumanizedContentEngine(BaseEngine):
    name = "humanized_content"
    description = "Rewrite copy to sound natural, not AI-generated"

    def __init__(self) -> None:
        super().__init__()
        self.ollama = get_ollama()

    def run(self, *, text: str, voice: str = "casual & confident") -> Dict[str, Any]:
        prompt = (
            f"Rewrite the following text in a natural, human voice ({voice}). "
            "Use contractions, vary sentence length, drop AI-tells like 'in conclusion', "
            "'furthermore', and rigid lists. Keep the meaning identical. "
            "Return ONLY the rewritten text.\n\nTEXT:\n" + text
        )
        try:
            new_text = self.ollama.generate(prompt, temperature=0.8,
                                             max_tokens=int(len(text.split()) * 2 + 80))
            new_text = new_text.strip().strip('"')
            return {"original": text, "humanized": new_text}
        except OllamaUnavailable:
            return {"original": text, "humanized": self._heuristic(text)}

    @staticmethod
    def _heuristic(text: str) -> str:
        replacements = {
            "in conclusion,": "so basically,",
            "furthermore,": "also,",
            "additionally,": "and,",
            "however,": "but,",
            "therefore,": "so,",
            "it is important to note that ": "",
            "in this article": "here",
            "let us": "let's",
            "do not": "don't",
            "cannot": "can't",
            "will not": "won't",
            "I am": "I'm",
            "you are": "you're",
        }
        out = text
        for k, v in replacements.items():
            out = re.sub(k, v, out, flags=re.IGNORECASE)
        return out


class CategoryRouterEngine(BaseEngine):
    name = "category_router"
    description = "Route a topic to its best-fit category/account"

    def run(self, *, topic: str,
            available_categories: Optional[List[str]] = None) -> Dict[str, Any]:
        text = topic.lower()
        scores: Dict[str, int] = {}
        for cat, kws in CATEGORY_KEYWORDS.items():
            scores[cat] = sum(1 for kw in kws if kw in text)
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        primary = ranked[0][0] if ranked and ranked[0][1] else "general"
        if available_categories:
            primary = next((c for c, _ in ranked
                            if c in available_categories and _ > 0), primary)
        return {
            "primary_category": primary,
            "scores": {c: s for c, s in ranked if s > 0} or {"general": 1},
            "confidence": min(1.0, ranked[0][1] / 3.0) if ranked else 0.0,
        }


class CompetitorEngine(BaseEngine):
    name = "competitor"
    description = "Concise competitor analysis using the local LLM"

    def __init__(self) -> None:
        super().__init__()
        self.ollama = get_ollama()

    def run(self, *, niche: str, region: str = "global",
            timeframe: str = "last 7 days") -> Dict[str, Any]:
        prompt = (
            f"Act as a content-intelligence analyst. Give a concise competitor scan for niche: {niche}, "
            f"region: {region}, timeframe: {timeframe}. "
            "Return ONLY JSON with: top_creators (5 name+angle), winning_formats, common_hooks, "
            "trending_audio_themes, content_gaps."
        )
        try:
            return self.ollama.generate_json(prompt, temperature=0.5, max_tokens=900)
        except OllamaUnavailable:
            return {
                "top_creators": [{"name": f"Top creator {i+1}",
                                  "angle": f"angle {i+1} on {niche}"} for i in range(5)],
                "winning_formats": ["short reel under 30s", "carousel of 5 slides",
                                    "talking-head story format"],
                "common_hooks": [
                    "Stop doing X like everyone else",
                    "3 things nobody told you about Y",
                    "I tried Z for 30 days",
                ],
                "trending_audio_themes": ["uplifting cinematic", "lo-fi chill", "trending pop"],
                "content_gaps": [f"Beginner explainers on {niche}", "Long-form deep dives",
                                 f"Region-specific takes on {niche}"],
            }
