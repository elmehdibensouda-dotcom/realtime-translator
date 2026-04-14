"""
Google Cloud Speech-to-Text v2 Streaming ASR Service
- Falls back to Google when Deepgram is not configured
- Uses gRPC streaming for low latency
"""

import asyncio
import logging
import time
from typing import AsyncGenerator

from app.core.config import settings
from app.core.metrics import metrics_registry
from app.models.transcript import TranscriptEvent, TranscriptType
from app.services.asr.base import BaseASRService

logger = logging.getLogger(__name__)


class GoogleASRService(BaseASRService):
    """Google Cloud Speech streaming ASR (v1 long-running stream)."""

    async def transcribe_stream(
        self,
        audio_chunks: AsyncGenerator[bytes, None],
        session_id: str,
    ) -> AsyncGenerator[TranscriptEvent, None]:
        try:
            from google.cloud import speech_v1 as speech
        except ImportError:
            logger.error("google-cloud-speech not installed. pip install google-cloud-speech")
            return

        client = speech.SpeechAsyncClient()

        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
            enable_automatic_punctuation=True,
            model="latest_long",
        )
        streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True,
        )

        seq = 0

        async def _request_generator():
            yield speech.StreamingRecognizeRequest(streaming_config=streaming_config)
            async for chunk in audio_chunks:
                if chunk:
                    yield speech.StreamingRecognizeRequest(audio_content=chunk)

        try:
            t0 = time.perf_counter()
            async for response in await client.streaming_recognize(_request_generator()):
                for result in response.results:
                    alt = result.alternatives[0] if result.alternatives else None
                    if not alt or not alt.transcript.strip():
                        continue
                    seq += 1
                    lat = (time.perf_counter() - t0) * 1000
                    metrics_registry.record_latency("asr_latency_ms", lat)
                    yield TranscriptEvent(
                        type=TranscriptType.FINAL if result.is_final else TranscriptType.PARTIAL,
                        session_id=session_id,
                        sequence=seq,
                        transcript_en=alt.transcript.strip(),
                        confidence=alt.confidence or 0.0,
                        asr_latency_ms=round(lat, 1),
                    )
                    t0 = time.perf_counter()
        except Exception as exc:
            logger.error("[%s] Google ASR error: %s", session_id, exc)
            metrics_registry.increment("asr_errors_total")

    async def close(self) -> None:
        pass
