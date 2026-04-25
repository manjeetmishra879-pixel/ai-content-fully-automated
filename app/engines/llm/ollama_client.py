"""
Thin wrapper around the Ollama HTTP API with retries and JSON-mode helpers.

The OLLAMA_BASE_URL env var (or settings.ollama_base_url) selects the server.
On Replit we run ollama on 127.0.0.1:8008.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


def _default_base_url() -> str:
    # Prefer explicit env var, then settings, then localhost:8008
    if url := os.environ.get("OLLAMA_BASE_URL"):
        return url.rstrip("/")
    try:
        from app.core.config import settings  # local import to avoid cycle
        return str(settings.ollama_base_url).rstrip("/")
    except Exception:  # pragma: no cover
        return "http://127.0.0.1:8008"


class OllamaUnavailable(RuntimeError):
    """Raised when the Ollama server is not reachable."""


class OllamaClient:
    """Synchronous client for the Ollama generate / chat endpoints."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout_seconds: float = 120.0,
    ) -> None:
        self.base_url = (base_url or _default_base_url()).rstrip("/")
        self.default_model = default_model or os.environ.get("OLLAMA_MODEL", "mistral")
        self.timeout = timeout_seconds
        self._client = httpx.Client(timeout=timeout_seconds)

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        try:
            r = self._client.get(f"{self.base_url}/api/version", timeout=3.0)
            return r.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        try:
            r = self._client.get(f"{self.base_url}/api/tags", timeout=5.0)
            r.raise_for_status()
            return [m.get("name", "") for m in r.json().get("models", [])]
        except Exception as exc:
            logger.debug("list_models failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(min=1, max=4),
        retry=retry_if_exception_type(httpx.RequestError),
        reraise=True,
    )
    def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        format_json: bool = False,
    ) -> str:
        """Single-shot text generation. Returns the response text."""
        payload: Dict[str, Any] = {
            "model": model or self.default_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system
        if max_tokens is not None:
            payload["options"]["num_predict"] = int(max_tokens)
        if stop:
            payload["options"]["stop"] = stop
        if format_json:
            payload["format"] = "json"

        try:
            r = self._client.post(f"{self.base_url}/api/generate", json=payload)
            r.raise_for_status()
            data = r.json()
            return (data.get("response") or "").strip()
        except httpx.HTTPStatusError as exc:
            # 404 = model not pulled yet; surface as unavailable so engines fall back.
            raise OllamaUnavailable(
                f"Ollama returned {exc.response.status_code} for model "
                f"{payload['model']}: {exc.response.text[:200]}"
            ) from exc
        except (httpx.RequestError, httpx.ConnectError) as exc:
            raise OllamaUnavailable(f"Ollama at {self.base_url} not reachable: {exc}") from exc

    def generate_json(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.4,
        max_tokens: Optional[int] = 1024,
    ) -> Dict[str, Any]:
        """Generate a JSON object. Falls back to extracting the first {...} block."""
        text = self.generate(
            prompt,
            model=model,
            system=system or "You are a helpful assistant. Respond ONLY with valid minified JSON.",
            temperature=temperature,
            max_tokens=max_tokens,
            format_json=True,
        )
        return self._safe_json_loads(text)

    @staticmethod
    def _safe_json_loads(text: str) -> Dict[str, Any]:
        text = (text or "").strip()
        if not text:
            return {}
        # Strip code-fences if present.
        text = re.sub(r"^```(?:json)?", "", text).rstrip("`").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Find first balanced JSON object.
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            return {"_raw": text}

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass


# A module-level singleton clients can share.
_default_client: Optional[OllamaClient] = None


def get_ollama() -> OllamaClient:
    global _default_client
    if _default_client is None:
        _default_client = OllamaClient()
    return _default_client
