"""
ABTestingEngine — manages multi-variant tests for hooks, thumbnails,
captions, music, and publishing times.

Uses a simple Thompson-sampling (Beta-distribution) bandit so the system
naturally moves traffic toward winning variants.
"""

from __future__ import annotations

import random
import uuid
from typing import Any, Dict, List, Optional

from app.engines.base import BaseEngine


class _Variant:
    __slots__ = ("id", "label", "payload", "wins", "losses", "impressions", "conversions")

    def __init__(self, label: str, payload: Any):
        self.id = uuid.uuid4().hex[:10]
        self.label = label
        self.payload = payload
        self.wins = 1.0  # Beta priors
        self.losses = 1.0
        self.impressions = 0
        self.conversions = 0

    def to_dict(self) -> Dict[str, Any]:
        rate = self.conversions / self.impressions if self.impressions else 0.0
        return {
            "id": self.id, "label": self.label, "payload": self.payload,
            "impressions": self.impressions, "conversions": self.conversions,
            "conversion_rate": round(rate, 4),
            "alpha": round(self.wins, 2), "beta": round(self.losses, 2),
        }


class ABTestingEngine(BaseEngine):
    name = "ab_testing"
    description = "Multi-variant testing using a Beta-Bernoulli bandit"

    def __init__(self) -> None:
        super().__init__()
        self._tests: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    def create_test(self, name: str, variants: List[Any]) -> Dict[str, Any]:
        if not variants or len(variants) < 2:
            raise ValueError("At least two variants are required.")
        test_id = uuid.uuid4().hex[:12]
        normalized: List[_Variant] = []
        for i, v in enumerate(variants):
            if isinstance(v, str):
                normalized.append(_Variant(v, None))
            elif isinstance(v, dict):
                normalized.append(_Variant(v.get("label", f"v{i}"), v.get("payload")))
            else:
                normalized.append(_Variant(str(v), None))
        self._tests[test_id] = {
            "id": test_id,
            "name": name,
            "status": "running",
            "variants": normalized,
        }
        return self._summary(test_id)

    def pick(self, test_id: str) -> Dict[str, Any]:
        test = self._require(test_id)
        # Thompson sample.
        best, best_sample = None, -1.0
        for v in test["variants"]:
            sample = random.betavariate(v.wins, v.losses)
            if sample > best_sample:
                best, best_sample = v, sample
        best.impressions += 1
        return {"test_id": test_id, "variant_id": best.id,
                "label": best.label, "payload": best.payload}

    def report(self, test_id: str, variant_id: str, *, converted: bool) -> Dict[str, Any]:
        test = self._require(test_id)
        for v in test["variants"]:
            if v.id == variant_id:
                if converted:
                    v.conversions += 1
                    v.wins += 1
                else:
                    v.losses += 1
                return self._summary(test_id)
        raise KeyError(f"Variant {variant_id} not found in test {test_id}")

    def declare_winner(self, test_id: str) -> Dict[str, Any]:
        test = self._require(test_id)
        scored = sorted(
            test["variants"],
            key=lambda v: (v.wins / (v.wins + v.losses)),
            reverse=True,
        )
        winner = scored[0]
        test["status"] = "completed"
        return {"test_id": test_id, "winner": winner.to_dict()}

    def list_tests(self) -> List[Dict[str, Any]]:
        return [self._summary(tid) for tid in self._tests]

    def run(self, action: str = "list", **kwargs: Any) -> Any:
        if action == "create":
            return self.create_test(kwargs["name"], kwargs["variants"])
        if action == "pick":
            return self.pick(kwargs["test_id"])
        if action == "report":
            return self.report(kwargs["test_id"], kwargs["variant_id"],
                                converted=kwargs.get("converted", False))
        if action == "winner":
            return self.declare_winner(kwargs["test_id"])
        return self.list_tests()

    # ------------------------------------------------------------------
    def _require(self, test_id: str) -> Dict[str, Any]:
        if test_id not in self._tests:
            raise KeyError(f"Test {test_id} not found")
        return self._tests[test_id]

    def _summary(self, test_id: str) -> Dict[str, Any]:
        t = self._tests[test_id]
        return {
            "id": t["id"], "name": t["name"], "status": t["status"],
            "variants": [v.to_dict() for v in t["variants"]],
        }
