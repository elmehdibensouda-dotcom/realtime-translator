import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from deep_translator import GoogleTranslator
from app.services.translation.base import BaseTranslationService

logger = logging.getLogger(__name__)

from app.services.translation.persistent_cache import translation_cache

class FreeTranslationService(BaseTranslationService):
    def __init__(self):
        # On crée un pool de threads pour traiter plusieurs traductions en parallèle
        self.executor = ThreadPoolExecutor(max_workers=10)

    async def translate(self, text: str) -> str:
        if not text.strip():
            return ""
        
        # 1. Vérification du cache permanent (0ms)
        cached = translation_cache.get(text)
        if cached:
            return cached
        
        def _do_translate(t):
            res = GoogleTranslator(source='en', target='fr').translate(t)
            # 2. Sauvegarde dans le cache pour la prochaine fois
            if res:
                translation_cache.set(t, res)
            return res

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(self.executor, _do_translate, text)
            return result
        except Exception as e:
            logger.error("Free Translation Error: %s", e)
            return f"[Error]"

    async def close(self):
        self.executor.shutdown()
