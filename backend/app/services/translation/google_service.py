"""
Google Cloud Translation fallback service.
Used when DeepL is unavailable or rate-limited.
"""

import asyncio
import logging

from app.core.config import settings
from app.core.metrics import LatencyTimer, metrics_registry
from app.services.translation.base import BaseTranslationService

logger = logging.getLogger(__name__)


class GoogleTranslationService(BaseTranslationService):
    def __init__(self) -> None:
        self._loop = asyncio.get_event_loop()
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google.cloud import translate_v2 as google_translate
            self._client = google_translate.Client()
        return self._client

    async def translate(self, text: str) -> str:
        if not text.strip():
            return ""
        client = self._get_client()
        with LatencyTimer("translation_latency_ms"):
            result = await self._loop.run_in_executor(
                None,
                lambda: client.translate(text, source_language="en", target_language="fr"),
            )
        translated = result.get("translatedText", "")
        metrics_registry.increment("translations_total")
        return translated

    async def close(self) -> None:
        self._client = None
