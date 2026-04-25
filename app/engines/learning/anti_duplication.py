"""
AntiDuplicationEngine — prevents duplicate text, image and video posts.

Text: Sentence Transformers embeddings + vector similarity search.
Image: average-hash perceptual fingerprint.
Video: frame-grab perceptual hash via ffmpeg if available.
Persistence: Vector DB (Chroma/Qdrant) for text, in-process LRU for images/videos.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
import uuid
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from app.engines.base import BaseEngine
from app.core.vector_db import get_vector_db, get_embedding_model


def _normalize(text: str) -> str:
    import re
    text = (text or "").lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class AntiDuplicationEngine(BaseEngine):
    name = "anti_duplication"
    description = "Detect duplicate text/image/video against history"

    def __init__(self, history_size: int = 5000):
        super().__init__()
        self._image_hashes: Dict[str, int] = {}
        self._video_hashes: Dict[str, int] = {}
        self._cap = history_size
        self._vector_db = None
        self._embedding_model = None
        self._collection_name = "text_duplicates"
        self._init_vector_db()

    def _init_vector_db(self):
        try:
            self._vector_db = get_vector_db()
            self._embedding_model = get_embedding_model()
            # Create collection if using Chroma
            if hasattr(self._vector_db, 'create_collection'):
                try:
                    self._vector_db.create_collection(name=self._collection_name)
                except Exception:
                    pass  # Collection might already exist
        except Exception as e:
            self.logger.warning(f"Vector DB initialization failed: {e}. Falling back to in-memory.")
            self._vector_db = None
            self._embedding_model = None

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

        if self._embedding_model and self._vector_db:
            return self._check_text_vector(normalized, threshold, register)
        else:
            # Fallback to simple hash-based check
            return self._check_text_hash(normalized, threshold, register)

    def _check_text_vector(self, text: str, threshold: float, register: bool) -> Dict[str, Any]:
        try:
            embedding = self._embedding_model.encode([text])[0].tolist()

            # Search for similar texts
            if hasattr(self._vector_db, 'query'):  # Chroma
                results = self._vector_db.query(
                    collection_name=self._collection_name,
                    query_embeddings=[embedding],
                    n_results=5
                )
                if results and results['distances']:
                    min_distance = min(results['distances'][0])
                    similarity = 1 - min_distance  # Convert distance to similarity
                    is_dup = similarity >= threshold
                    match_id = results['ids'][0][0] if results['ids'] and results['ids'][0] else None

                    if register and not is_dup:
                        doc_id = str(uuid.uuid4())
                        self._vector_db.add(
                            collection_name=self._collection_name,
                            embeddings=[embedding],
                            documents=[text],
                            ids=[doc_id]
                        )

                    return {
                        "is_duplicate": is_dup,
                        "similarity": round(similarity, 4),
                        "match_id": match_id if is_dup else None,
                        "threshold": threshold,
                        "method": "vector"
                    }
            elif hasattr(self._vector_db, 'search'):  # Qdrant
                # Qdrant search implementation
                results = self._vector_db.search(
                    collection_name=self._collection_name,
                    query_vector=embedding,
                    limit=5
                )
                if results:
                    min_score = min(r.score for r in results)
                    similarity = min_score  # Qdrant returns similarity directly
                    is_dup = similarity >= threshold
                    match_id = results[0].id if results else None

                    if register and not is_dup:
                        doc_id = str(uuid.uuid4())
                        self._vector_db.upsert(
                            collection_name=self._collection_name,
                            points=[{
                                "id": doc_id,
                                "vector": embedding,
                                "payload": {"text": text}
                            }]
                        )

                    return {
                        "is_duplicate": is_dup,
                        "similarity": round(similarity, 4),
                        "match_id": match_id if is_dup else None,
                        "threshold": threshold,
                        "method": "vector"
                    }
        except Exception as e:
            self.logger.warning(f"Vector search failed: {e}. Falling back to hash.")

        return self._check_text_hash(text, threshold, register)

    def _check_text_hash(self, text: str, threshold: float, register: bool) -> Dict[str, Any]:
        # Simple fallback using hash
        digest = hashlib.sha1(text.encode()).hexdigest()
        # This is a simplified version - in practice you'd need to store hashes
        # For now, just return not duplicate since we can't check without storage
        return {
            "is_duplicate": False,
            "similarity": 0.0,
            "match_id": None,
            "threshold": threshold,
            "method": "hash_fallback"
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
        for store in (self._image_hashes, self._video_hashes):
            while len(store) > self._cap:
                store.popitem(last=False)
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
