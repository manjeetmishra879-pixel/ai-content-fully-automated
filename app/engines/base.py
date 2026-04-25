"""
Base engine class and engine registry.

All AI engines inherit from BaseEngine and self-register so they can be
discovered and invoked dynamically.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_REGISTRY: Dict[str, "BaseEngine"] = {}


def register_engine(name: str, instance: "BaseEngine") -> None:
    if name in _REGISTRY:
        logger.warning("Engine %s already registered; replacing", name)
    _REGISTRY[name] = instance


def get_engine(name: str) -> "BaseEngine":
    if name not in _REGISTRY:
        raise KeyError(f"Engine '{name}' is not registered. Available: {list(_REGISTRY)}")
    return _REGISTRY[name]


def list_engines() -> List[str]:
    return sorted(_REGISTRY.keys())


def all_engines() -> Dict[str, "BaseEngine"]:
    return dict(_REGISTRY)


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------


class BaseEngine(ABC):
    """Common base for all engines."""

    name: ClassVar[str] = "base"
    description: ClassVar[str] = "Abstract base engine"

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"engine.{self.name}")
        self._invocations = 0
        self._last_run_ms: Optional[float] = None
        self._last_error: Optional[str] = None
        register_engine(self.name, self)

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Synchronous main entry point for the engine."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        self._invocations += 1
        try:
            result = self.run(*args, **kwargs)
            self._last_error = None
            return result
        except Exception as exc:  # noqa: BLE001
            self._last_error = f"{type(exc).__name__}: {exc}"
            self.logger.exception("Engine %s failed", self.name)
            raise
        finally:
            self._last_run_ms = (time.perf_counter() - start) * 1000.0

    def stats(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "invocations": self._invocations,
            "last_run_ms": self._last_run_ms,
            "last_error": self._last_error,
        }

    def health(self) -> Dict[str, Any]:
        """Override per-engine for richer health checks (e.g. external service ping)."""
        return {"name": self.name, "ok": True}
