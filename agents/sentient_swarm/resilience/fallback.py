"""
Fallback strategies for graceful degradation.
"""

from abc import ABC, abstractmethod
from typing import Any, List


class FallbackStrategy(ABC):
    """Abstract fallback strategy."""

    @abstractmethod
    async def execute(self, error: Exception) -> Any:
        """Execute fallback."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if fallback is available."""
        pass


class FallbackChain:
    """
    Chain of fallback strategies.
    Tries each until one succeeds.
    """

    def __init__(self, strategies: List[FallbackStrategy]):
        self.strategies = strategies

    async def execute(self, error: Exception) -> Any:
        """Execute fallback chain."""
        for strategy in self.strategies:
            if not strategy.is_available():
                continue

            try:
                return await strategy.execute(error)
            except Exception:
                continue

        raise FallbackExhausted(f"All fallbacks failed for: {error}")


class FallbackExhausted(Exception):
    """All fallback strategies failed."""

    pass
