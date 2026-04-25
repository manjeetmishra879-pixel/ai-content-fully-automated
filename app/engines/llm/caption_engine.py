"""
CaptionEngine — produces platform-native captions from a base script.

Per platform we tailor: length, hashtag density, emoji usage, line breaks.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.engines.base import BaseEngine
from app.engines.llm.content_engine import PLATFORM_LIMITS
from app.engines.llm.ollama_client import OllamaUnavailable, get_ollama


class CaptionEngine(BaseEngine):
    name = "caption"
    description = "Generate platform-native captions from a script"

    def __init__(self) -> None:
        super().__init__()
        self.ollama = get_ollama()

    def run(
        self,
        script: str,
        *,
        platforms: List[str],
        hashtags: Optional[List[str]] = None,
        cta: Optional[str] = None,
        language: str = "english",
    ) -> Dict[str, str]:
        hashtags = hashtags or []
        out: Dict[str, str] = {}
        for p in platforms:
            try:
                out[p] = self._generate_for_platform(script, p, hashtags, cta, language)
            except OllamaUnavailable:
                out[p] = self._fallback(script, p, hashtags, cta)
        return out

    def _generate_for_platform(
        self,
        script: str,
        platform: str,
        hashtags: List[str],
        cta: Optional[str],
        language: str,
    ) -> str:
        limits = PLATFORM_LIMITS.get(platform, {"caption": 2200, "hashtags": 5, "tone": "neutral"})
        max_chars = int(limits["caption"])
        max_tags = int(limits["hashtags"])
        tone = limits["tone"]

        prompt = (
            f"Rewrite this script as a NATIVE {platform} caption in {language}. "
            f"Tone: {tone}. Hard length limit: {max_chars} chars. "
            f"Use natural line breaks. End with this CTA if provided: {cta or 'none'}. "
            f"Then append up to {max_tags} hashtags from this pool (skip if list is empty): "
            f"{hashtags}. Return ONLY the caption text, no preamble.\n\n"
            f"SCRIPT:\n{script}"
        )
        text = self.ollama.generate(prompt, temperature=0.7, max_tokens=600).strip()
        return self._clean(text, max_chars, max_tags, hashtags)

    @staticmethod
    def _clean(text: str, max_chars: int, max_tags: int, hashtag_pool: List[str]) -> str:
        text = re.sub(r"^['\"]|['\"]$", "", text).strip()
        # If model didn't add tags, append from pool.
        if max_tags > 0 and "#" not in text and hashtag_pool:
            tags = " ".join(hashtag_pool[:max_tags])
            text = f"{text}\n\n{tags}"
        return text[:max_chars]

    @staticmethod
    def _fallback(script: str, platform: str, hashtags: List[str], cta: Optional[str]) -> str:
        limits = PLATFORM_LIMITS.get(platform, {"caption": 2200, "hashtags": 5})
        max_chars = int(limits["caption"])
        max_tags = int(limits["hashtags"])
        body = script.strip()
        suffix = ""
        if cta:
            suffix += f"\n\n👉 {cta}"
        if max_tags and hashtags:
            suffix += "\n\n" + " ".join(hashtags[:max_tags])
        out = (body + suffix)[:max_chars]
        return out
