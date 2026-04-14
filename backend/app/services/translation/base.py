"""
Abstract base for all translation providers.
"""

from abc import ABC, abstractmethod


class BaseTranslationService(ABC):
    """Translate a single English string to French."""

    @abstractmethod
    async def translate(self, text: str) -> str:
        """Return translated French text or raise on failure."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Release any persistent HTTP sessions."""
        ...
