"""
VideoEngine — assembles short-form videos using FFmpeg.

Pipeline:
  inputs (image OR clip) + voice WAV + subtitles → vertical 1080x1920 MP4
"""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.engines.base import BaseEngine
from app.engines.media.image_engine import STORAGE_ROOT

VIDEO_DIR = STORAGE_ROOT / "videos"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")


def ffmpeg_available() -> bool:
    return FFMPEG is not None


def _probe_duration(path: str) -> float:
    if not FFPROBE or not os.path.exists(path):
        return 0.0
    try:
        out = subprocess.check_output(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            stderr=subprocess.DEVNULL, timeout=15,
        ).decode().strip()
        return float(out or 0.0)
    except Exception:
        return 0.0


class VideoEngine(BaseEngine):
    name = "video"
    description = "Render vertical short-form videos with FFmpeg"

    def run(
        self,
        *,
        background_image: Optional[str] = None,
        background_video: Optional[str] = None,
        voice_path: Optional[str] = None,
        subtitle_path: Optional[str] = None,
        duration: Optional[float] = None,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
    ) -> Dict[str, Any]:
        if not ffmpeg_available():
            return {"path": None, "error": "ffmpeg is not installed in this environment"}

        if not background_image and not background_video:
            return {"path": None, "error": "background_image or background_video is required"}

        target_duration = duration or (_probe_duration(voice_path) if voice_path else 8.0)
        target_duration = max(2.0, float(target_duration))

        out_path = VIDEO_DIR / f"video_{uuid.uuid4().hex[:10]}.mp4"
        cmd: List[str] = [FFMPEG, "-y"]

        # Visual input
        if background_video:
            cmd += ["-stream_loop", "-1", "-i", background_video]
        else:
            cmd += ["-loop", "1", "-i", background_image]

        # Audio input
        if voice_path and os.path.exists(voice_path):
            cmd += ["-i", voice_path]

        # Video filter
        vf = f"scale={width}:{height}:force_original_aspect_ratio=increase," \
             f"crop={width}:{height},format=yuv420p"
        if subtitle_path and os.path.exists(subtitle_path):
            # ffmpeg subtitles filter requires escaping
            esc = subtitle_path.replace(":", r"\:").replace(",", r"\,")
            vf += f",subtitles='{esc}':force_style='Fontsize=18,Outline=2,BorderStyle=3'"

        cmd += ["-vf", vf, "-r", str(fps), "-t", f"{target_duration:.2f}"]
        if voice_path:
            cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                    "-c:a", "aac", "-b:a", "128k", "-shortest"]
        else:
            cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-an"]

        cmd += [str(out_path)]

        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", "ignore")[-1500:]
            return {"path": None, "error": f"ffmpeg failed: {stderr}"}
        except subprocess.TimeoutExpired:
            return {"path": None, "error": "ffmpeg timed out"}

        return {
            "path": str(out_path),
            "url": f"/media/videos/{out_path.name}",
            "duration_s": round(target_duration, 2),
            "size": [width, height],
            "fps": fps,
        }
