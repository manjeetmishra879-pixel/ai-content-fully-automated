"""
ContentEngine — generates scripts, hooks, captions, hashtags, CTAs, titles.

Backed by a local Ollama LLM (Mistral by default). When the LLM is offline
the engine falls back to deterministic templates so the API never breaks.
"""

from __future__ import annotations

import random
import re
from typing import Any, Dict, List, Optional

from app.engines.base import BaseEngine
from app.engines.llm.ollama_client import OllamaUnavailable, get_ollama


PLATFORM_LIMITS = {
    "instagram": {"caption": 2200, "hashtags": 30, "tone": "punchy + emoji"},
    "tiktok": {"caption": 2200, "hashtags": 5, "tone": "raw + meme"},
    "youtube": {"caption": 5000, "hashtags": 15, "tone": "story-driven"},
    "youtube_shorts": {"caption": 1000, "hashtags": 5, "tone": "fast hook + payoff"},
    "facebook": {"caption": 63206, "hashtags": 5, "tone": "warm + community"},
    "x": {"caption": 280, "hashtags": 3, "tone": "sharp + witty"},
    "twitter": {"caption": 280, "hashtags": 3, "tone": "sharp + witty"},
    "linkedin": {"caption": 3000, "hashtags": 5, "tone": "professional + insight"},
    "telegram": {"caption": 4096, "hashtags": 5, "tone": "broadcast + bold"},
    "threads": {"caption": 500, "hashtags": 5, "tone": "conversational"},
}

DURATION_TARGETS = {
    "reel": 30,
    "short": 30,
    "youtube_shorts": 45,
    "tiktok": 30,
    "story": 15,
    "carousel": 90,
    "long_form": 300,
    "post": 0,
    "tweet": 0,
}


class ContentEngine(BaseEngine):
    name = "content"
    description = "Generate scripts, hooks, hashtags, CTAs and captions"

    def __init__(self) -> None:
        super().__init__()
        self.ollama = get_ollama()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(
        self,
        topic: str,
        *,
        content_type: str = "reel",
        platforms: Optional[List[str]] = None,
        tone: str = "energetic",
        language: str = "english",
        hashtag_count: int = 10,
        include_cta: bool = True,
        trends: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        platforms = platforms or ["instagram"]
        duration = DURATION_TARGETS.get(content_type, 30)
        trend_block = ", ".join(trends) if trends else ""

        prompt = self._build_prompt(
            topic=topic,
            content_type=content_type,
            tone=tone,
            language=language,
            duration=duration,
            platforms=platforms,
            trends=trend_block,
            include_cta=include_cta,
            hashtag_count=hashtag_count,
        )

        try:
            data = self.ollama.generate_json(prompt, temperature=0.8, max_tokens=1400)
            if not data or "_raw" in data and "script" not in data:
                raise OllamaUnavailable("Empty or invalid LLM response")
        except (OllamaUnavailable, Exception) as exc:  # noqa: BLE001
            self.logger.warning("LLM unavailable, using template fallback: %s", exc)
            data = self._template_fallback(topic, tone, content_type, platforms)

        # Normalise + post-process
        return self._normalise(data, topic, platforms, hashtag_count, include_cta)

    # ------------------------------------------------------------------
    # Prompt
    # ------------------------------------------------------------------
    def _build_prompt(
        self,
        *,
        topic: str,
        content_type: str,
        tone: str,
        language: str,
        duration: int,
        platforms: List[str],
        trends: str,
        include_cta: bool,
        hashtag_count: int,
    ) -> str:
        cta_clause = "Include 3 strong call-to-action lines." if include_cta else "Skip CTAs."
        trend_clause = f"Weave these trending angles when natural: {trends}." if trends else ""
        platform_caps = "\n".join(
            f"- {p}: max {PLATFORM_LIMITS.get(p, {}).get('caption', 2200)} chars, "
            f"tone hint: {PLATFORM_LIMITS.get(p, {}).get('tone', 'neutral')}"
            for p in platforms
        )
        return f"""You are an elite short-form content strategist.
Produce a viral content package for the following brief.

TOPIC: {topic}
CONTENT TYPE: {content_type} (~{duration}s if video)
TONE: {tone}
LANGUAGE: {language}
TARGET PLATFORMS: {", ".join(platforms)}
{trend_clause}
{cta_clause}

Return ONLY a valid JSON object with this exact shape:
{{
  "title": "string, max 80 chars, no quotes",
  "script": "the full spoken/written script, plain text, no markdown",
  "hooks": ["5 distinct opening hooks under 14 words each"],
  "ctas": ["3 short calls to action"],
  "hashtags": ["{hashtag_count} relevant hashtags WITHOUT the # symbol"],
  "captions": {{
{",".join(f'    "{p}": "platform-tailored caption"' for p in platforms)}
  }},
  "keywords": ["8 SEO keywords"],
  "music_mood": "one short phrase describing ideal background music",
  "thumbnail_concept": "one short phrase describing ideal thumbnail"
}}

Per-platform caption guidance:
{platform_caps}

The script must be punchy, structured (Hook → Body → Climax → CTA),
and feel native to the platform. Do NOT include any prose outside the JSON.
"""

    # ------------------------------------------------------------------
    # Fallback (no LLM)
    # ------------------------------------------------------------------
    def _template_fallback(
        self, topic: str, tone: str, content_type: str, platforms: List[str]
    ) -> Dict[str, Any]:
        topic_clean = topic.strip().rstrip(".") or "today's topic"
        hooks = [
            f"Stop scrolling — here's the truth about {topic_clean}.",
            f"3 things nobody tells you about {topic_clean}.",
            f"I tried {topic_clean} for 30 days. Here's what happened.",
            f"Why {topic_clean} is everywhere right now.",
            f"The {topic_clean} mistake costing you results.",
        ]
        script = (
            f"Most people get {topic_clean} completely wrong. "
            f"Here's what actually works. First, focus on the one thing that compounds. "
            f"Second, remove what doesn't move the needle. "
            f"Third, ship something tiny today — momentum beats perfection. "
            f"Save this if you needed the reminder."
        )
        captions = {p: f"{hooks[0]} {script[:160]}…" for p in platforms}
        return {
            "title": f"{topic_clean.title()} — what actually works",
            "script": script,
            "hooks": hooks,
            "ctas": [
                "Save this for later.",
                "Follow for more.",
                "Tag a friend who needs this.",
            ],
            "hashtags": [
                re.sub(r"[^a-zA-Z0-9]", "", topic_clean.replace(" ", "")) or "viral",
                "fyp", "explore", "trending", "creator", "growth",
                "mindset", "valuepost", "reels", "shorts",
            ],
            "captions": captions,
            "keywords": topic_clean.split() + ["growth", "tips", "viral"],
            "music_mood": "uplifting cinematic build",
            "thumbnail_concept": f"Bold text overlay: {topic_clean.upper()} with split-screen visual",
        }

    # ------------------------------------------------------------------
    # Normalisation
    # ------------------------------------------------------------------
    def _normalise(
        self,
        data: Dict[str, Any],
        topic: str,
        platforms: List[str],
        hashtag_count: int,
        include_cta: bool,
    ) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        out["title"] = (data.get("title") or topic.title()).strip()[:120]
        out["script"] = (data.get("script") or "").strip()
        out["hooks"] = self._coerce_list(data.get("hooks"), 5)
        out["ctas"] = self._coerce_list(data.get("ctas"), 3) if include_cta else []
        # Hashtags: strip leading #, dedupe, lowercase, cap to count.
        raw_tags = self._coerce_list(data.get("hashtags"), hashtag_count or 10)
        seen, hashtags = set(), []
        for t in raw_tags:
            tag = re.sub(r"[^a-zA-Z0-9_]", "", str(t).lstrip("#")).lower()
            if tag and tag not in seen:
                seen.add(tag)
                hashtags.append(f"#{tag}")
            if hashtag_count and len(hashtags) >= hashtag_count:
                break
        out["hashtags"] = hashtags

        # Captions: ensure one per platform, respect platform caption limits.
        captions_in = data.get("captions") or {}
        if isinstance(captions_in, list):
            captions_in = {p: c for p, c in zip(platforms, captions_in)}
        captions: Dict[str, str] = {}
        for p in platforms:
            text = (captions_in.get(p) or out["script"][:200]).strip()
            limit = PLATFORM_LIMITS.get(p, {}).get("caption", 2200)
            captions[p] = text[: int(limit)]
        out["captions"] = captions

        out["keywords"] = self._coerce_list(data.get("keywords"), 8)
        out["music_mood"] = (data.get("music_mood") or "uplifting cinematic build").strip()
        out["thumbnail_concept"] = (
            data.get("thumbnail_concept") or f"Bold text on {topic[:40]}"
        ).strip()
        return out

    @staticmethod
    def _coerce_list(value: Any, target: int) -> List[str]:
        if not value:
            return []
        if isinstance(value, str):
            items = [v.strip(" -*\t") for v in re.split(r"[\n;|]+", value) if v.strip()]
        elif isinstance(value, list):
            items = [str(v).strip() for v in value if str(v).strip()]
        else:
            items = [str(value)]
        # Pad if too few to keep API stable.
        if 0 < len(items) < target:
            items = items + items[: target - len(items)]
        return items[:target] if target else items
