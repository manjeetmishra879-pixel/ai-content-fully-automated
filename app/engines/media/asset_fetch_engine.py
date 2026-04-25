"""
AssetFetchEngine — fetches stock imagery from Pexels / Pixabay.

Both APIs are free with a key. If no key is configured we return an
empty list rather than failing, so callers can fall back to local
image generation.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from app.engines.base import BaseEngine
from app.engines.media.image_engine import STORAGE_ROOT

CACHE_DIR = STORAGE_ROOT / "stock"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class AssetFetchEngine(BaseEngine):
    name = "asset_fetch"
    description = "Fetch stock images/videos from Pexels and Pixabay"

    def __init__(self) -> None:
        super().__init__()
        self.pexels_key = os.environ.get("PEXELS_API_KEY", "")
        self.pixabay_key = os.environ.get("PIXABAY_API_KEY", "")

    # ------------------------------------------------------------------
    def run(
        self,
        query: str,
        *,
        media_type: str = "image",
        limit: int = 10,
        download: bool = False,
        orientation: str = "portrait",
    ) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        sources_used: List[str] = []

        if self.pexels_key:
            try:
                results += self._pexels(query, media_type, limit, orientation)
                sources_used.append("pexels")
            except Exception as exc:
                self.logger.warning("Pexels failed: %s", exc)

        if len(results) < limit and self.pixabay_key:
            try:
                results += self._pixabay(query, media_type, limit, orientation)
                sources_used.append("pixabay")
            except Exception as exc:
                self.logger.warning("Pixabay failed: %s", exc)

        results = results[:limit]
        if download:
            for asset in results:
                local = self._download(asset["url"])
                if local:
                    asset["local_path"] = local
                    asset["local_url"] = f"/media/stock/{Path(local).name}"

        return {
            "query": query,
            "media_type": media_type,
            "sources": sources_used or ["none"],
            "count": len(results),
            "assets": results,
            "warning": None if sources_used else
                "No PEXELS_API_KEY or PIXABAY_API_KEY configured.",
        }

    # ------------------------------------------------------------------
    def _pexels(self, query: str, media_type: str, limit: int, orientation: str) -> List[Dict[str, Any]]:
        headers = {"Authorization": self.pexels_key}
        if media_type == "video":
            url = f"https://api.pexels.com/videos/search?query={query}&per_page={limit}&orientation={orientation}"
            r = httpx.get(url, headers=headers, timeout=15.0); r.raise_for_status()
            out = []
            for v in r.json().get("videos", []):
                files = v.get("video_files", [])
                best = max(files, key=lambda f: f.get("width", 0)) if files else {}
                out.append({"id": v.get("id"), "url": best.get("link"),
                            "preview": v.get("image"), "width": best.get("width"),
                            "height": best.get("height"), "source": "pexels",
                            "credit": (v.get("user") or {}).get("name")})
            return out
        url = f"https://api.pexels.com/v1/search?query={query}&per_page={limit}&orientation={orientation}"
        r = httpx.get(url, headers=headers, timeout=15.0); r.raise_for_status()
        return [{"id": p.get("id"), "url": (p.get("src") or {}).get("large2x"),
                 "preview": (p.get("src") or {}).get("medium"),
                 "width": p.get("width"), "height": p.get("height"),
                 "source": "pexels", "credit": p.get("photographer")}
                for p in r.json().get("photos", [])]

    def _pixabay(self, query: str, media_type: str, limit: int, orientation: str) -> List[Dict[str, Any]]:
        endpoint = "videos/" if media_type == "video" else ""
        url = (f"https://pixabay.com/api/{endpoint}?key={self.pixabay_key}&q={query}"
               f"&per_page={max(3, min(limit, 200))}&orientation={'vertical' if orientation == 'portrait' else 'horizontal'}")
        r = httpx.get(url, timeout=15.0); r.raise_for_status()
        items = r.json().get("hits", [])
        out = []
        for item in items[:limit]:
            if media_type == "video":
                v = (item.get("videos") or {}).get("medium", {})
                out.append({"id": item.get("id"), "url": v.get("url"),
                            "preview": item.get("picture_id"),
                            "width": v.get("width"), "height": v.get("height"),
                            "source": "pixabay", "credit": item.get("user")})
            else:
                out.append({"id": item.get("id"),
                            "url": item.get("largeImageURL") or item.get("webformatURL"),
                            "preview": item.get("previewURL"),
                            "width": item.get("imageWidth"),
                            "height": item.get("imageHeight"),
                            "source": "pixabay", "credit": item.get("user")})
        return out

    def _download(self, url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        h = hashlib.sha1(url.encode()).hexdigest()[:12]
        ext = ".mp4" if url.lower().rsplit(".", 1)[-1] in {"mp4", "mov", "webm"} else ".jpg"
        path = CACHE_DIR / f"{h}{ext}"
        if path.exists():
            return str(path)
        try:
            with httpx.stream("GET", url, timeout=30.0) as r:
                r.raise_for_status()
                with open(path, "wb") as f:
                    for chunk in r.iter_bytes(chunk_size=65536):
                        f.write(chunk)
            return str(path)
        except Exception as exc:
            self.logger.warning("Download failed for %s: %s", url, exc)
            return None
