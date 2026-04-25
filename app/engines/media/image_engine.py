"""
ImageEngine — generates quote cards, thumbnails, banners, posters using Pillow.

CPU-only, no external API needed. Output is a PNG file under storage/images/.
"""

from __future__ import annotations

import os
import textwrap
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.engines.base import BaseEngine

STORAGE_ROOT = Path(os.environ.get("MEDIA_STORAGE", "storage")).resolve()
IMAGES_DIR = STORAGE_ROOT / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


# Try to find a system font; fall back to Pillow's default bitmap font.
def _font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/nix/store",  # search prefix
        "/usr/share/fonts",
    ]
    # Common families to try.
    names = [
        "DejaVuSans-Bold.ttf", "DejaVuSans.ttf",
        "Inter-Bold.ttf", "Inter.ttf",
        "Roboto-Bold.ttf", "Arial.ttf",
    ]
    found: Optional[str] = None
    for root in candidates:
        if not os.path.isdir(root):
            continue
        for dirpath, _, files in os.walk(root):
            for name in names:
                if name in files:
                    found = os.path.join(dirpath, name)
                    break
            if found:
                break
        if found:
            break
    try:
        return ImageFont.truetype(found, size) if found else ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


PRESETS: Dict[str, Tuple[int, int]] = {
    "instagram_post": (1080, 1080),
    "instagram_story": (1080, 1920),
    "reel": (1080, 1920),
    "youtube_thumbnail": (1280, 720),
    "youtube_short": (1080, 1920),
    "twitter_card": (1200, 675),
    "facebook_post": (1200, 630),
    "linkedin_post": (1200, 627),
    "banner": (1500, 500),
    "poster": (1080, 1350),
}


GRADIENTS = [
    ((20, 30, 70), (90, 30, 110)),
    ((10, 60, 90), (200, 90, 60)),
    ((30, 30, 30), (120, 0, 60)),
    ((10, 10, 30), (60, 120, 200)),
    ((20, 80, 60), (200, 180, 70)),
    ((90, 20, 60), (250, 130, 60)),
]


class ImageEngine(BaseEngine):
    name = "image"
    description = "Generate quote cards, thumbnails, banners and posters"

    def run(
        self,
        text: str,
        *,
        preset: str = "instagram_post",
        subtitle: Optional[str] = None,
        accent: Optional[str] = None,
        gradient_index: Optional[int] = None,
        watermark: Optional[str] = None,
    ) -> Dict[str, Any]:
        size = PRESETS.get(preset, PRESETS["instagram_post"])
        gi = gradient_index if gradient_index is not None else (abs(hash(text)) % len(GRADIENTS))
        top, bottom = GRADIENTS[gi]
        img = self._gradient(size, top, bottom)
        self._add_noise(img)

        draw = ImageDraw.Draw(img)
        w, h = size

        # Headline
        max_chars = max(12, w // 38)
        lines = textwrap.wrap(text, width=max_chars)
        font_size = max(48, min(int(w / 12), int(h / (len(lines) + 2) / 1.6)))
        font = _font(font_size)
        line_h = int(font_size * 1.2)
        block_h = line_h * len(lines)
        y = (h - block_h) // 2 - (40 if subtitle else 0)
        for line in lines:
            tw = draw.textlength(line, font=font)
            x = (w - tw) // 2
            self._shadowed_text(draw, (x, y), line, font, "white")
            y += line_h

        if subtitle:
            sf = _font(max(28, font_size // 3))
            tw = draw.textlength(subtitle, font=sf)
            self._shadowed_text(draw, ((w - tw) // 2, y + 24), subtitle, sf,
                                accent or "#ffd166")

        if watermark:
            wf = _font(28)
            draw.text((24, h - 48), watermark, fill=(255, 255, 255, 220), font=wf)

        out_path = IMAGES_DIR / f"{preset}_{uuid.uuid4().hex[:10]}.png"
        img.convert("RGB").save(out_path, "PNG", optimize=True)
        return {
            "path": str(out_path),
            "preset": preset,
            "size": list(size),
            "url": f"/media/images/{out_path.name}",
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _gradient(size: Tuple[int, int], top: Tuple[int, int, int],
                  bottom: Tuple[int, int, int]) -> Image.Image:
        w, h = size
        base = Image.new("RGB", size, top)
        px = base.load()
        for y in range(h):
            t = y / max(1, h - 1)
            r = int(top[0] + (bottom[0] - top[0]) * t)
            g = int(top[1] + (bottom[1] - top[1]) * t)
            b = int(top[2] + (bottom[2] - top[2]) * t)
            for x in range(w):
                px[x, y] = (r, g, b)
        return base

    @staticmethod
    def _add_noise(img: Image.Image) -> None:
        # Soft blur to give a film feel, no heavy randomness needed.
        blurred = img.filter(ImageFilter.GaussianBlur(radius=1))
        img.paste(blurred)

    @staticmethod
    def _shadowed_text(draw: ImageDraw.ImageDraw, xy: Tuple[int, int], text: str,
                       font: ImageFont.ImageFont, fill: str) -> None:
        x, y = xy
        # Drop shadow
        for dx, dy in [(2, 2), (3, 3)]:
            draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 180))
        draw.text((x, y), text, font=font, fill=fill)


class ThumbnailEngine(BaseEngine):
    """Specialized thumbnail generator with bold text + accent shape."""

    name = "thumbnail"
    description = "Generate YouTube/short-video thumbnails"

    def __init__(self) -> None:
        super().__init__()
        self.image = ImageEngine()

    def run(
        self,
        title: str,
        *,
        subtitle: Optional[str] = None,
        platform: str = "youtube_thumbnail",
        accent: str = "#ff3366",
    ) -> Dict[str, Any]:
        return self.image(title, preset=platform, subtitle=subtitle, accent=accent)
