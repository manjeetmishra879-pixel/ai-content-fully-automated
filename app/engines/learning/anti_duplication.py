"""
AntiDuplicationEngine — prevents duplicate text, image and video posts.

Text: SHA-1 of normalized text + Jaccard similarity over shingles.
Image: average-hash perceptual fingerprint.
Video: frame-grab perceptual hash via ffmpeg if available.
Persistence: in-process LRU + Postgres `duplicates` table when wired in.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from app.engines.base import BaseEngine


def _normalize(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _shingles(text: str, k: int = 4) -> Set[str]:
    tokens = _normalize(text).split()
    if len(tokens) < k:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i:i + k]) for i in range(len(tokens) - k + 1)}


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class AntiDuplicationEngine(BaseEngine):
    name = "anti_duplication"
    description = "Detect duplicate text/image/video against history"

    def __init__(self, history_size: int = 5000):
        super().__init__()
        self._text_hashes: "OrderedDict[str, str]" = OrderedDict()
        self._text_shingles: "OrderedDict[str, Set[str]]" = OrderedDict()
        self._image_hashes: "OrderedDict[str, int]" = OrderedDict()
        self._video_hashes: "OrderedDict[str, int]" = OrderedDict()
        self._cap = history_size

    def run(self, kind: str = "text", **kwargs: Any) -> Dict[str, Any]:
        if kind == "text":
            return self.check_text(kwargs["text"], threshold=kwargs.get("threshold", 0.85))
        if kind == "image":
            return self.check_image(kwargs["path"], threshold=kwargs.get("threshold", 6))
        if kind == "video":
            return self.check_video(kwargs["path"], threshold=kwargs.get("threshold", 8))
        raise ValueError("kind must be text|image|video")

    # ------------------------------------------------------------------
    def check_text(self, text: str, *, threshold: float = 0.85,
                   register: bool = True) -> Dict[str, Any]:
        normalized = _normalize(text)
        if not normalized:
            return {"is_duplicate": False, "reason": "empty"}
        digest = hashlib.sha1(normalized.encode()).hexdigest()
        if digest in self._text_hashes.values():
            return {"is_duplicate": True, "reason": "exact_hash", "similarity": 1.0}

        shingles = _shingles(normalized)
        best_id, best_sim = None, 0.0
        for tid, prior in self._text_shingles.items():
            sim = _jaccard(shingles, prior)
            if sim > best_sim:
                best_sim, best_id = sim, tid
        is_dup = best_sim >= threshold

        if register and not is_dup:
            new_id = digest[:10]
            self._text_hashes[new_id] = digest
            self._text_shingles[new_id] = shingles
            self._evict()

        return {
            "is_duplicate": is_dup,
            "similarity": round(best_sim, 4),
            "match_id": best_id if is_dup else None,
            "threshold": threshold,
        }

    def check_image(self, path: str, *, threshold: int = 6,
                    register: bool = True) -> Dict[str, Any]:
        if not os.path.exists(path):
            return {"is_duplicate": False, "reason": "missing_file"}
        ahash = self._average_hash(path)
        best_id, best_dist = None, 64
        for iid, prior in self._image_hashes.items():
            dist = bin(ahash ^ prior).count("1")
            if dist < best_dist:
                best_dist, best_id = dist, iid
        is_dup = best_dist <= threshold

        if register and not is_dup:
            new_id = hashlib.sha1(path.encode()).hexdigest()[:10]
            self._image_hashes[new_id] = ahash
            self._evict()

        return {"is_duplicate": is_dup, "hamming_distance": best_dist,
                "match_id": best_id if is_dup else None, "threshold": threshold}

    def check_video(self, path: str, *, threshold: int = 8,
                    register: bool = True) -> Dict[str, Any]:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return {"is_duplicate": False, "reason": "ffmpeg_missing"}
        if not os.path.exists(path):
            return {"is_duplicate": False, "reason": "missing_file"}
        with tempfile.TemporaryDirectory() as tmp:
            frame = os.path.join(tmp, "f.png")
            try:
                subprocess.run(
                    [ffmpeg, "-y", "-ss", "1", "-i", path, "-frames:v", "1", frame],
                    check=True, capture_output=True, timeout=60,
                )
            except Exception as exc:
                return {"is_duplicate": False, "reason": f"ffprobe failed: {exc}"}
            ahash = self._average_hash(frame)
        best_id, best_dist = None, 64
        for vid, prior in self._video_hashes.items():
            dist = bin(ahash ^ prior).count("1")
            if dist < best_dist:
                best_dist, best_id = dist, vid
        is_dup = best_dist <= threshold
        if register and not is_dup:
            new_id = hashlib.sha1(path.encode()).hexdigest()[:10]
            self._video_hashes[new_id] = ahash
            self._evict()
        return {"is_duplicate": is_dup, "hamming_distance": best_dist,
                "match_id": best_id if is_dup else None, "threshold": threshold}

    # ------------------------------------------------------------------
    @staticmethod
    def _average_hash(path: str, size: int = 8) -> int:
        from PIL import Image  # local import
        img = Image.open(path).convert("L").resize((size, size), Image.LANCZOS)
        pixels = list(img.getdata())
        avg = sum(pixels) / len(pixels)
        bits = 0
        for i, p in enumerate(pixels):
            if p > avg:
                bits |= 1 << i
        return bits

    def _evict(self) -> None:
        for store in (self._text_hashes, self._text_shingles,
                      self._image_hashes, self._video_hashes):
            while len(store) > self._cap:
                store.popitem(last=False)
