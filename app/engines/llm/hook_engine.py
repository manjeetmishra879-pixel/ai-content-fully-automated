"""
HookEngine — generates and ranks viral opening hooks.

Hooks are the single biggest predictor of retention on short-form video.
This engine produces several candidates and scores them with a simple
heuristic so callers can pick the best one or A/B test the top N.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.engines.base import BaseEngine
from app.engines.llm.ollama_client import OllamaUnavailable, get_ollama


HIGH_VALUE_TOKENS = {
    "stop", "secret", "nobody", "wrong", "truth", "mistake", "shocking",
    "warning", "never", "always", "instantly", "before", "why", "how",
    "this", "rules", "myth", "biggest", "fastest", "free", "you", "your",
}


class HookEngine(BaseEngine):
    name = "hook"
    description = "Generate and rank viral opening hooks"

    def __init__(self) -> None:
        super().__init__()
        self.ollama = get_ollama()

    def run(
        self,
        topic: str,
        *,
        count: int = 8,
        style: str = "shock+curiosity",
        platform: str = "instagram",
        language: str = "english",
    ) -> Dict[str, Any]:
        prompt = (
            f"Generate {count} viral opening hooks for {platform} content about: {topic}.\n"
            f"Language: {language}. Style: {style}. Each hook must be under 14 words, "
            f"create instant curiosity or pattern interrupt, and avoid hashtags.\n"
            'Return ONLY JSON: {"hooks": ["...", "..."]}.'
        )
        try:
            data = self.ollama.generate_json(prompt, temperature=0.9, max_tokens=600)
            hooks = data.get("hooks") or []
        except OllamaUnavailable as exc:
            self.logger.warning("LLM unavailable, fallback hooks: %s", exc)
            hooks = self._fallback_hooks(topic, count)

        if not hooks:
            hooks = self._fallback_hooks(topic, count)

        scored = [{"text": h.strip(), "score": self._score(h)} for h in hooks if isinstance(h, str)]
        scored.sort(key=lambda x: x["score"], reverse=True)
        return {"hooks": scored[:count], "best": scored[0]["text"] if scored else None}

    # ------------------------------------------------------------------
    @staticmethod
    def _score(hook: str) -> float:
        text = (hook or "").lower()
        words = re.findall(r"[a-zA-Z']+", text)
        if not words:
            return 0.0
        length = len(words)
        # Sweet spot: 6–12 words.
        length_score = max(0.0, 1.0 - abs(9 - length) / 9.0)
        token_hits = sum(1 for w in words if w in HIGH_VALUE_TOKENS)
        token_score = min(1.0, token_hits / 3.0)
        question_bonus = 0.15 if hook.strip().endswith("?") else 0.0
        number_bonus = 0.15 if re.search(r"\b\d+\b", hook) else 0.0
        return round(60 + 25 * length_score + 15 * token_score + 100 * (question_bonus + number_bonus) / 2, 2)

    @staticmethod
    def _fallback_hooks(topic: str, count: int) -> List[str]:
        t = topic.strip().rstrip(".")
        templates = [
            f"Stop doing {t} like everyone else.",
            f"3 things nobody told you about {t}.",
            f"The biggest mistake in {t}.",
            f"Why {t} is broken in 2026.",
            f"I tried {t} for 30 days — here's the truth.",
            f"This {t} secret changed everything.",
            f"You're doing {t} wrong if you skip this.",
            f"How to win at {t} in under 60 seconds.",
            f"What experts won't tell you about {t}.",
            f"The fastest way to master {t}.",
        ]
        return templates[:count]
