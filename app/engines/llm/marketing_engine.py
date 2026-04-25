"""
MarketingEngine — generates marketing creatives & multi-channel campaigns
from a brief or website snapshot.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from app.engines.base import BaseEngine
from app.engines.llm.ollama_client import OllamaUnavailable, get_ollama


class MarketingEngine(BaseEngine):
    name = "marketing"
    description = "Generate marketing creatives, ad copy and campaign plans"

    def __init__(self) -> None:
        super().__init__()
        self.ollama = get_ollama()

    def run(
        self,
        *,
        business_name: Optional[str] = None,
        website_url: Optional[str] = None,
        offer: Optional[str] = None,
        audience: Optional[str] = None,
        channels: Optional[List[str]] = None,
        tone: str = "bold + benefit-led",
        language: str = "english",
    ) -> Dict[str, Any]:
        channels = channels or ["instagram", "facebook", "google_search", "youtube"]
        site_snapshot = self._scrape(website_url) if website_url else {}
        brief = {
            "business_name": business_name or site_snapshot.get("title") or "Your Brand",
            "offer": offer or site_snapshot.get("meta_description") or "",
            "audience": audience or "general consumers",
            "tone": tone,
            "language": language,
            "channels": channels,
        }
        try:
            campaign = self._llm_campaign(brief)
        except OllamaUnavailable as exc:
            self.logger.warning("Marketing fallback: %s", exc)
            campaign = self._fallback_campaign(brief)

        return {"brief": brief, "site_snapshot": site_snapshot, "campaign": campaign}

    # ------------------------------------------------------------------
    def _scrape(self, url: str) -> Dict[str, Any]:
        try:
            r = httpx.get(url, timeout=10.0, follow_redirects=True,
                          headers={"User-Agent": "Mozilla/5.0 ContentBot/1.0"})
            html = r.text
        except Exception as exc:
            self.logger.warning("Scrape failed for %s: %s", url, exc)
            return {"url": url, "error": str(exc)}

        title = self._first(re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S))
        desc = self._first(
            re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html, re.I)
        )
        og_image = self._first(
            re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](.*?)["\']', html, re.I)
        )
        # Heuristic colour extraction from inline styles.
        colors = list({c for c in re.findall(r"#(?:[0-9a-fA-F]{3}){1,2}\b", html)})[:6]
        domain = urlparse(url).netloc
        return {
            "url": url,
            "domain": domain,
            "title": title or domain,
            "meta_description": desc,
            "og_image": og_image,
            "palette": colors,
        }

    @staticmethod
    def _first(match) -> Optional[str]:
        return match.group(1).strip() if match else None

    # ------------------------------------------------------------------
    def _llm_campaign(self, brief: Dict[str, Any]) -> Dict[str, Any]:
        prompt = (
            "You are a senior performance-marketing strategist. Build a launch campaign.\n"
            f"Brand: {brief['business_name']}\nOffer: {brief['offer']}\n"
            f"Audience: {brief['audience']}\nTone: {brief['tone']}\n"
            f"Language: {brief['language']}\nChannels: {', '.join(brief['channels'])}\n\n"
            "Return ONLY a JSON object with this shape:\n"
            "{\n"
            '  "positioning": "one-sentence positioning",\n'
            '  "hero_headlines": ["6 ad headlines under 9 words"],\n'
            '  "primary_texts": ["4 punchy primary ad bodies"],\n'
            '  "ctas": ["5 distinct CTAs"],\n'
            '  "value_props": ["5 benefit bullets"],\n'
            '  "audiences": ["4 audience targeting ideas"],\n'
            '  "keywords": ["10 keywords for search ads"],\n'
            '  "creative_concepts": [{"format":"reel|carousel|static|video|story", "concept":"..."}],\n'
            '  "channel_plan": [{"channel":"...", "budget_share_pct":25, "objective":"..."}],\n'
            '  "kpis": ["4 KPIs to track"]\n'
            "}"
        )
        return self.ollama.generate_json(prompt, temperature=0.6, max_tokens=1400)

    # ------------------------------------------------------------------
    def _fallback_campaign(self, brief: Dict[str, Any]) -> Dict[str, Any]:
        name = brief["business_name"]
        offer = brief["offer"] or f"discover {name}"
        return {
            "positioning": f"{name} helps {brief['audience']} win at {offer}.",
            "hero_headlines": [
                f"Meet {name} — built for results.",
                f"{name}: {offer}",
                f"Stop guessing. Start with {name}.",
                f"The smarter way to {offer}.",
                f"Real outcomes with {name}.",
                f"Try {name} risk-free today.",
            ],
            "primary_texts": [
                f"{name} makes {offer} effortless. Join thousands who switched this month.",
                f"Built for {brief['audience']}. Crafted for results. {name} delivers.",
                f"Get more from your day with {name}. Tap to learn more.",
                f"You're one tap away from {offer}. {name} is ready.",
            ],
            "ctas": ["Try free", "Start now", "See how it works", "Get the offer", "Book a demo"],
            "value_props": [
                "Fast set-up", "Proven results", "Loved by customers",
                "Backed by experts", "Cancel anytime",
            ],
            "audiences": [
                f"Lookalike of past buyers", f"Interest: {brief['audience']}",
                "Retargeting site visitors (30d)", "High-intent search keywords",
            ],
            "keywords": [name.lower(), offer, "best", "review", "vs", "alternative",
                         "how to", "guide", "near me", "online"],
            "creative_concepts": [
                {"format": "reel", "concept": f"Founder talking head explaining the {offer} problem"},
                {"format": "carousel", "concept": f"5-slide value-prop walkthrough of {name}"},
                {"format": "static", "concept": f"Hero shot + headline: {name}"},
                {"format": "story", "concept": "Behind the scenes / testimonial cut-down"},
            ],
            "channel_plan": [
                {"channel": c, "budget_share_pct": int(100 / max(1, len(brief["channels"]))),
                 "objective": "conversions"} for c in brief["channels"]
            ],
            "kpis": ["CAC", "ROAS", "CTR", "Conversion rate"],
        }
