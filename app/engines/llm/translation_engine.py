"""
TranslationEngine — translate any text into a target language.

Strategy: use the local LLM (it handles many language pairs well) with a
strict instruction to return only the translated text. On failure we
return the original text so callers don't crash.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.engines.base import BaseEngine
from app.engines.llm.ollama_client import OllamaUnavailable, get_ollama


SUPPORTED = {
    "english", "hindi", "hinglish", "spanish", "french", "german",
    "portuguese", "arabic", "indonesian", "bengali", "tamil", "telugu",
    "marathi", "gujarati", "punjabi", "urdu", "japanese", "korean",
    "chinese", "russian", "italian", "turkish", "dutch", "vietnamese",
    "thai", "swahili", "persian",
}


class TranslationEngine(BaseEngine):
    name = "translation"
    description = "Translate text into another language using the local LLM"

    def __init__(self) -> None:
        super().__init__()
        self.ollama = get_ollama()
        self._cache: Dict[str, str] = {}

    def run(
        self,
        text: str,
        *,
        target_language: str,
        source_language: Optional[str] = None,
        preserve_formatting: bool = True,
    ) -> Dict[str, Any]:
        target = target_language.strip().lower()
        if not text or not text.strip():
            return {"translated": "", "target": target, "cached": False}

        cache_key = f"{target}::{hash(text)}"
        if cache_key in self._cache:
            return {"translated": self._cache[cache_key], "target": target, "cached": True}

        instruction = (
            f"Translate the following text into {target_language}. "
            f"{'Preserve line breaks and emojis exactly. ' if preserve_formatting else ''}"
            f"Return ONLY the translated text, no quotes, no commentary."
        )
        if source_language:
            instruction = f"Source language is {source_language}. " + instruction

        try:
            translated = self.ollama.generate(
                f"{instruction}\n\nTEXT:\n{text}",
                temperature=0.2,
                max_tokens=max(256, int(len(text) * 1.5) + 64),
            ).strip()
        except OllamaUnavailable as exc:
            self.logger.warning("Translation fallback (no LLM): %s", exc)
            translated = text

        if not translated:
            translated = text

        self._cache[cache_key] = translated
        return {"translated": translated, "target": target, "cached": False}

    def batch(
        self,
        texts: List[str],
        *,
        target_language: str,
        source_language: Optional[str] = None,
    ) -> List[str]:
        return [
            self.run(t, target_language=target_language, source_language=source_language)["translated"]
            for t in texts
        ]
