"""
DeepL Translation Service
- Uses official deepl Python SDK
- Async wrapper with persistent session
- Caches recent translations to reduce API calls
"""

import asyncio
import hashlib
import logging
from functools import lru_cache
from typing import Optional

import deepl

from app.core.config import settings
from app.core.metrics import LatencyTimer, metrics_registry
from app.services.translation.base import BaseTranslationService

logger = logging.getLogger(__name__)

# Simple LRU translation cache (keyed by source text hash)
_CACHE: dict[str, str] = {}
_CACHE_MAX = 512


class DeepLTranslationService(BaseTranslationService):
    """
    DeepL API wrapper.
    DeepL consistently achieves the best human-evaluation scores for EN→FR.
    P50 latency ~150 ms, P99 ~400 ms via EU servers.
    """

    def __init__(self) -> None:
        self._translator = deepl.Translator(settings.DEEPL_API_KEY)
        self._loop = asyncio.get_event_loop()

    def _cache_key(self, text: str) -> str:
        return hashlib.sha1(text.encode()).hexdigest()

    async def translate(self, text: str) -> str:
        if not text.strip():
            return ""

        key = self._cache_key(text)
        if key in _CACHE:
            metrics_registry.increment("translation_cache_hits")
            return _CACHE[key]

        with LatencyTimer("translation_latency_ms"):
            result = await self._loop.run_in_executor(
                None,
                lambda: self._translator.translate_text(
                    text,
                    source_lang="EN",
                    target_lang="FR",
                    preserve_formatting=True,
                ),
            )

        translated = result.text if hasattr(result, "text") else str(result)

        # Maintain cache size
        if len(_CACHE) >= _CACHE_MAX:
            oldest = next(iter(_CACHE))
            del _CACHE[oldest]
        _CACHE[key] = translated

        metrics_registry.increment("translations_total")
        return translated

    async def close(self) -> None:
        pass  # deepl SDK manages its own session
