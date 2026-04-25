"""
VoiceEngine — text-to-speech narration.

Strategy (in priority order):
  1. Coqui TTS (local, high quality) — only if installed.
  2. pyttsx3 / espeak system command — offline but lower quality.
  3. Silent placeholder WAV with the spoken duration estimated.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid
import wave
from pathlib import Path
from typing import Any, Dict, Optional

from app.engines.base import BaseEngine
from app.engines.media.image_engine import STORAGE_ROOT

VOICE_DIR = STORAGE_ROOT / "voice"
VOICE_DIR.mkdir(parents=True, exist_ok=True)


def _coqui_available() -> bool:
    try:
        import TTS  # noqa: F401
        return True
    except Exception:
        return False


def _espeak_path() -> Optional[str]:
    return shutil.which("espeak-ng") or shutil.which("espeak")


class VoiceEngine(BaseEngine):
    name = "voice"
    description = "Text-to-speech narration with multi-backend fallback"

    def __init__(self) -> None:
        super().__init__()
        self._coqui = None  # lazy load

    # ------------------------------------------------------------------
    def run(
        self,
        text: str,
        *,
        language: str = "en",
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> Dict[str, Any]:
        text = (text or "").strip()
        if not text:
            return {"path": None, "backend": "none", "duration_s": 0}

        out_path = VOICE_DIR / f"voice_{uuid.uuid4().hex[:10]}.wav"

        if _coqui_available():
            try:
                return self._coqui_tts(text, str(out_path), language)
            except Exception as exc:
                self.logger.warning("Coqui TTS failed, falling back: %s", exc)

        espeak = _espeak_path()
        if espeak:
            try:
                return self._espeak_tts(text, str(out_path), language, speed, espeak)
            except Exception as exc:
                self.logger.warning("eSpeak failed, falling back: %s", exc)

        return self._silent_placeholder(text, str(out_path))

    # ------------------------------------------------------------------
    def _coqui_tts(self, text: str, out_path: str, language: str) -> Dict[str, Any]:
        if self._coqui is None:
            from TTS.api import TTS  # type: ignore
            model_name = (
                "tts_models/multilingual/multi-dataset/xtts_v2"
                if language not in {"en", "english"}
                else "tts_models/en/ljspeech/tacotron2-DDC"
            )
            self._coqui = TTS(model_name=model_name, progress_bar=False, gpu=False)
        self._coqui.tts_to_file(text=text, file_path=out_path)
        return {"path": out_path, "backend": "coqui", "duration_s": _wav_duration(out_path),
                "url": f"/media/voice/{Path(out_path).name}"}

    def _espeak_tts(self, text: str, out_path: str, language: str,
                    speed: float, espeak: str) -> Dict[str, Any]:
        wpm = max(80, min(280, int(170 * speed)))
        lang_map = {"english": "en", "hindi": "hi", "spanish": "es", "french": "fr",
                    "german": "de", "italian": "it", "portuguese": "pt"}
        lang = lang_map.get(language.lower(), language[:2])
        cmd = [espeak, "-v", lang, "-s", str(wpm), "-w", out_path, text]
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        return {"path": out_path, "backend": "espeak", "duration_s": _wav_duration(out_path),
                "url": f"/media/voice/{Path(out_path).name}"}

    def _silent_placeholder(self, text: str, out_path: str) -> Dict[str, Any]:
        # Estimate ~150 wpm and write a silent WAV of that length so the
        # downstream video pipeline still has a valid audio track.
        words = max(1, len(text.split()))
        duration = max(1.0, words / 2.5)  # ~150 wpm
        framerate = 22050
        n_frames = int(duration * framerate)
        with wave.open(out_path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(framerate)
            w.writeframes(b"\x00\x00" * n_frames)
        return {"path": out_path, "backend": "silent",
                "duration_s": round(duration, 2),
                "url": f"/media/voice/{Path(out_path).name}",
                "warning": "No TTS backend installed; produced silent placeholder."}


def _wav_duration(path: str) -> float:
    try:
        with wave.open(path, "rb") as w:
            return round(w.getnframes() / float(w.getframerate()), 2)
    except Exception:
        return 0.0
