import pytest
import asyncio
from app.services.translation.free_service import FreeTranslationService

@pytest.mark.asyncio
async def test_free_translation_basic():
    service = FreeTranslationService()
    result = await service.translate("Hello world")
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0
    await service.close()

@pytest.mark.asyncio
async def test_free_translation_empty():
    service = FreeTranslationService()
    result = await service.translate("")
    assert result == ""
    await service.close()

@pytest.mark.asyncio
async def test_free_translation_caching():
    service = FreeTranslationService()
    text = "Unique test sentence for cache"
    
    # First call (real or from persistent cache)
    res1 = await service.translate(text)
    
    # Second call should be instant (memory cache)
    import time
    start = time.time()
    res2 = await service.translate(text)
    end = time.time()
    
    assert res1 == res2
    assert (end - start) < 0.01  # Should be near-instant
    await service.close()
