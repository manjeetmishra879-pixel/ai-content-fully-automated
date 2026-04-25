"""
Three creative-optimization engines:

  - EmotionalResonanceEngine: scores emotional pull and suggests tweaks.
  - AttentionOptimizerEngine: identifies attention drops and recommends fixes.
  - VisualEnhancementEngine: suggests visual treatments to boost retention.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.engines.base import BaseEngine


EMOTION_LEXICON = {
    "joy": {"happy", "joy", "delight", "love", "win", "amazing", "wonderful"},
    "anger": {"angry", "hate", "rage", "furious", "betray"},
    "fear": {"fear", "scared", "afraid", "danger", "warning", "risk"},
    "surprise": {"shocking", "unbelievable", "wow", "stunned", "incredible", "secret"},
    "sadness": {"sad", "lonely", "lost", "broken", "cry"},
    "trust": {"proven", "guaranteed", "trusted", "verified", "real"},
    "anticipation": {"soon", "next", "tomorrow", "watch", "wait", "coming"},
    "disgust": {"gross", "wrong", "toxic", "fake", "ugly"},
}


class EmotionalResonanceEngine(BaseEngine):
    name = "emotional_resonance"
    description = "Score emotional resonance and suggest tweaks"

    def run(self, *, script: str, target: Optional[List[str]] = None) -> Dict[str, Any]:
        text = (script or "").lower()
        words = re.findall(r"[a-zA-Z']+", text)
        scores: Dict[str, int] = {}
        for emotion, lex in EMOTION_LEXICON.items():
            scores[emotion] = sum(1 for w in words if w in lex)

        total_signals = sum(scores.values()) or 1
        distribution = {k: round(v / total_signals, 3) for k, v in scores.items()}
        primary = max(scores, key=scores.get) if total_signals > 1 else "neutral"
        intensity = round(min(100.0, total_signals * 8.0), 2)

        recommendations: List[str] = []
        if intensity < 30:
            recommendations.append("Add at least one strong emotional word in the first 3 seconds.")
        if target:
            for emotion in target:
                if scores.get(emotion, 0) == 0:
                    recommendations.append(f"Inject '{emotion}' lexicon (e.g. {sorted(EMOTION_LEXICON.get(emotion, []))[:3]}).")
        if not recommendations:
            recommendations.append("Resonance is healthy — push hook intensity for top-of-funnel.")

        return {
            "primary_emotion": primary,
            "intensity": intensity,
            "distribution": distribution,
            "recommendations": recommendations,
        }


class AttentionOptimizerEngine(BaseEngine):
    name = "attention_optimizer"
    description = "Detect attention drops and recommend fixes"

    def run(self, *, script: str, duration_s: float = 30.0) -> Dict[str, Any]:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", script) if s.strip()]
        if not sentences:
            return {"drops": [], "recommendations": ["Script is empty."]}

        # Estimate timing per sentence by word count.
        weights = [max(1, len(s.split())) for s in sentences]
        total = sum(weights)
        timeline: List[Dict[str, Any]] = []
        cursor = 0.0
        for s, w in zip(sentences, weights):
            dur = duration_s * (w / total)
            risk = self._risk(s)
            timeline.append({
                "start": round(cursor, 2),
                "end": round(cursor + dur, 2),
                "text": s,
                "risk": risk,
            })
            cursor += dur

        drops = [t for t in timeline if t["risk"] >= 0.6]
        recommendations: List[str] = []
        if not timeline[0]["text"][:80].lower().startswith(
                ("stop", "you", "this", "what", "why", "how", "the", "i ")):
            recommendations.append("Open with a pattern-interrupt word (Stop / You / Why).")
        if any(t["risk"] >= 0.6 for t in timeline[1:4]):
            recommendations.append("Tighten seconds 2-6 — viewer is most likely to swipe here.")
        if duration_s > 45 and timeline[-1]["risk"] >= 0.5:
            recommendations.append("End with payoff or loop-back to hook to close the loop.")
        if not recommendations:
            recommendations.append("Pacing looks good. Consider a mid-roll callback at 50%.")

        return {
            "duration_s": duration_s,
            "timeline": timeline,
            "drops": drops,
            "recommendations": recommendations,
        }

    @staticmethod
    def _risk(sentence: str) -> float:
        words = sentence.split()
        risk = 0.0
        if len(words) > 24: risk += 0.4
        if len(words) < 4:  risk += 0.2
        if not re.search(r"[!?]", sentence): risk += 0.1
        if "and" in [w.lower() for w in words[:3]]: risk += 0.2
        return round(min(1.0, risk), 2)


class VisualEnhancementEngine(BaseEngine):
    name = "visual_enhancement"
    description = "Suggest visual treatments to boost retention"

    def run(
        self,
        *,
        script: str,
        platform: str = "instagram",
        duration_s: float = 30.0,
    ) -> Dict[str, Any]:
        words = script.lower()
        suggestions: List[str] = []
        if "first" in words or "1." in words:
            suggestions.append("Add numbered text overlays for each step (1/3, 2/3, 3/3).")
        if "you" in words:
            suggestions.append("Cut to direct-camera shot whenever the script says 'you'.")
        if duration_s >= 30:
            suggestions.append("Insert a B-roll cut every 2-3 seconds to maintain stimulation.")
        if platform in ("instagram", "tiktok", "youtube_shorts"):
            suggestions.append("Burn captions in the lower-third with high-contrast outline.")
            suggestions.append("Use vertical 9:16 framing with the subject on the upper third.")
        if "secret" in words or "shocking" in words:
            suggestions.append("Use zoom-in punch effect on the reveal moment.")
        if not suggestions:
            suggestions.append("Add motion text and a 0.3s zoom punch at every key beat.")

        return {
            "platform": platform,
            "duration_s": duration_s,
            "visual_suggestions": suggestions,
            "color_scheme": ["#0F0F1E", "#FFD166", "#EF476F"],
            "font_style": "Bold sans (Inter/DejaVu) with 4px outline + drop shadow",
        }
