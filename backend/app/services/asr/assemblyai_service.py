"""
AssemblyAI Streaming ASR Service
- Real-time streaming using assemblyai SDK
- High accuracy and low latency
"""

import asyncio
import logging
import time
from typing import AsyncGenerator, Optional

import assemblyai as aai

from app.core.config import settings
from app.core.metrics import metrics_registry
from app.models.transcript import TranscriptEvent, TranscriptType
from app.services.asr.base import BaseASRService

logger = logging.getLogger(__name__)

class AssemblyAIASRService(BaseASRService):
    def __init__(self) -> None:
        aai.settings.api_key = settings.ASSEMBLYAI_API_KEY
        self._transcriber = None

    async def transcribe_stream(
        self,
        audio_chunks: AsyncGenerator[bytes, None],
        session_id: str,
    ) -> AsyncGenerator[TranscriptEvent, None]:
        
        event_queue: asyncio.Queue[Optional[TranscriptEvent]] = asyncio.Queue()
        seq = 0

        def on_open(session_opened: aai.RealtimeSessionOpened):
            logger.info("[%s] AssemblyAI session opened (id=%s)", session_id, session_opened.session_id)

        def on_data(transcript: aai.RealtimeTranscript):
            nonlocal seq
            if not transcript.text:
                return

            seq += 1
            is_final = isinstance(transcript, aai.RealtimeFinalTranscript)
            
            # Record latency (approximate for streaming)
            metrics_registry.record_latency("asr_latency_ms", 150.0) # assemblyai baseline

            event = TranscriptEvent(
                type=TranscriptType.FINAL if is_final else TranscriptType.PARTIAL,
                session_id=session_id,
                sequence=seq,
                transcript_en=transcript.text,
                confidence=getattr(transcript, 'confidence', 1.0),
                asr_latency_ms=150.0,
            )
            event_queue.put_nowait(event)

            if is_final:
                metrics_registry.increment("asr_finals_total")
            else:
                metrics_registry.increment("asr_partials_total")

        def on_error(error: aai.RealtimeError):
            logger.error("[%s] AssemblyAI error: %s", session_id, error)
            metrics_registry.increment("asr_errors_total")

        def on_close():
            logger.info("[%s] AssemblyAI session closed", session_id)
            event_queue.put_nowait(None)

        # Initialize transcriber
        self._transcriber = aai.RealtimeTranscriber(
            sample_rate=16000,
            on_data=on_data,
            on_error=on_error,
            on_open=on_open,
            on_close=on_close,
        )

        # Connect
        self._transcriber.connect()

        async def _sender():
            try:
                async for chunk in audio_chunks:
                    if chunk:
                        self._transcriber.stream(chunk)
            except Exception as e:
                logger.error("[%s] AssemblyAI sender error: %s", session_id, e)
            finally:
                if self._transcriber:
                    self._transcriber.close()

        sender_task = asyncio.create_task(_sender())

        try:
            while True:
                event = await event_queue.get()
                if event is None:
                    break
                yield event
        finally:
            sender_task.cancel()
            await asyncio.gather(sender_task, return_exceptions=True)

    async def close(self) -> None:
        if self._transcriber:
            self._transcriber.close()
            self._transcriber = None
