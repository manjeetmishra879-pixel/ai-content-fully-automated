"""
SubtitleEngine — produces SRT/VTT subtitles.

Priority:
  1. faster-whisper transcription if an audio path is supplied AND faster-whisper is installed.
  2. Naive script-based timing distribution (split by sentence, assign even durations).
"""

from __future__ import annotations

import math
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.engines.base import BaseEngine
from app.engines.media.image_engine import STORAGE_ROOT

SUB_DIR = STORAGE_ROOT / "subtitles"
SUB_DIR.mkdir(parents=True, exist_ok=True)


def _faster_whisper_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except Exception:
        return False


class SubtitleEngine(BaseEngine):
    name = "subtitle"
    description = "Generate SRT/VTT subtitles from script or audio"

    def run(
        self,
        *,
        script: Optional[str] = None,
        audio_path: Optional[str] = None,
        duration_s: Optional[float] = None,
        format: str = "srt",
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        if audio_path and _faster_whisper_available():
            cues = self._whisper(audio_path, language=language)
        elif script:
            cues = self._from_script(script, duration_s or self._estimate_duration(script))
        else:
            return {"path": None, "warning": "Provide script or audio_path"}

        out_path = SUB_DIR / f"sub_{uuid.uuid4().hex[:10]}.{format}"
        text = self._render_srt(cues) if format == "srt" else self._render_vtt(cues)
        out_path.write_text(text, encoding="utf-8")
        return {"path": str(out_path), "format": format, "cues": len(cues),
                "url": f"/media/subtitles/{out_path.name}"}

    # ------------------------------------------------------------------
    def _whisper(self, audio_path: str, language: Optional[str]) -> List[Tuple[float, float, str]]:
        from faster_whisper import WhisperModel  # type: ignore
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio_path, language=language, beam_size=1)
        return [(seg.start, seg.end, seg.text.strip()) for seg in segments if seg.text.strip()]

    @staticmethod
    def _from_script(script: str, total_duration: float) -> List[Tuple[float, float, str]]:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", script.strip()) if s.strip()]
        if not sentences:
            return []
        weights = [max(1, len(s.split())) for s in sentences]
        total_weight = sum(weights)
        cues = []
        cursor = 0.0
        for sentence, weight in zip(sentences, weights):
            dur = total_duration * (weight / total_weight)
            cues.append((cursor, cursor + dur, sentence))
            cursor += dur
        return cues

    @staticmethod
    def _estimate_duration(script: str) -> float:
        # 150 wpm baseline.
        return max(2.0, len(script.split()) / 2.5)

    @staticmethod
    def _format_ts(t: float, vtt: bool = False) -> str:
        h = int(t // 3600); m = int((t % 3600) // 60); s = int(t % 60)
        ms = int(round((t - math.floor(t)) * 1000))
        sep = "." if vtt else ","
        return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"

    def _render_srt(self, cues: List[Tuple[float, float, str]]) -> str:
        lines = []
        for i, (start, end, text) in enumerate(cues, 1):
            lines.append(str(i))
            lines.append(f"{self._format_ts(start)} --> {self._format_ts(end)}")
            lines.append(text)
            lines.append("")
        return "\n".join(lines)

    def _render_vtt(self, cues: List[Tuple[float, float, str]]) -> str:
        lines = ["WEBVTT", ""]
        for start, end, text in cues:
            lines.append(f"{self._format_ts(start, vtt=True)} --> {self._format_ts(end, vtt=True)}")
            lines.append(text)
            lines.append("")
        return "\n".join(lines)
