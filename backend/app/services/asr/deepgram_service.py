"""
Deepgram Streaming ASR Service
- Uses Deepgram Nova-2 model (best WER + lowest latency)
- Real WebSocket streaming via deepgram-sdk
- Yields PARTIAL and FINAL TranscriptEvents
- Auto-reconnects on network failure
"""

import asyncio
import logging
import time
from typing import AsyncGenerator

from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveOptions,
    LiveTranscriptionEvents,
)

from app.core.config import settings
from app.core.metrics import LatencyTimer, metrics_registry
from app.models.transcript import TranscriptEvent, TranscriptType
from app.services.asr.base import BaseASRService

logger = logging.getLogger(__name__)

_DG_OPTIONS = LiveOptions(
    model="nova-2",
    language="en-US",
    encoding="linear16",
    sample_rate=16000,
    channels=1,
    interim_results=True,
    utterance_end_ms="1000",       # flush utterance after 1 s silence
    vad_events=True,
    punctuate=True,
    smart_format=True,
    endpointing=300,               # ms of silence → final
)

_MAX_RECONNECT_ATTEMPTS = 5
_RECONNECT_DELAY_BASE = 1.0        # seconds (exponential backoff)


class DeepgramASRService(BaseASRService):
    def __init__(self) -> None:
        self._client = DeepgramClient(
            settings.DEEPGRAM_API_KEY,
            config=DeepgramClientOptions(verbose=False),
        )
        self._connection = None

    async def transcribe_stream(
        self,
        audio_chunks: AsyncGenerator[bytes, None],
        session_id: str,
    ) -> AsyncGenerator[TranscriptEvent, None]:
        """Async generator – yields events as Deepgram responds."""

        event_queue: asyncio.Queue[TranscriptEvent | None] = asyncio.Queue()
        seq = 0

        def on_transcript(_, result, **__):
            nonlocal seq
            try:
                alt = result.channel.alternatives[0]
                text = alt.transcript.strip()
                if not text:
                    return

                is_final = result.is_final
                seq += 1
                start_ts = getattr(result, "_request_ts", time.time())
                latency_ms = (time.time() - start_ts) * 1000
                metrics_registry.record_latency("asr_latency_ms", latency_ms)

                event = TranscriptEvent(
                    type=TranscriptType.FINAL if is_final else TranscriptType.PARTIAL,
                    session_id=session_id,
                    sequence=seq,
                    transcript_en=text,
                    confidence=alt.confidence or 0.0,
                    asr_latency_ms=round(latency_ms, 1),
                )
                event_queue.put_nowait(event)

                if is_final:
                    metrics_registry.increment("asr_finals_total")
                else:
                    metrics_registry.increment("asr_partials_total")
            except Exception as exc:
                logger.warning("Deepgram callback error: %s", exc)

        def on_error(_, error, **__):
            logger.error("Deepgram error: %s", error)
            metrics_registry.increment("asr_errors_total")

        def on_close(_, **__):
            logger.info("[%s] Deepgram connection closed", session_id)
            event_queue.put_nowait(None)   # sentinel

        # ── Connect ──────────────────────────────────────────────────────────
        attempt = 0
        while attempt < _MAX_RECONNECT_ATTEMPTS:
            try:
                conn = self._client.listen.asyncwebsocket.v("1")
                conn.on(LiveTranscriptionEvents.Transcript, on_transcript)
                conn.on(LiveTranscriptionEvents.Error, on_error)
                conn.on(LiveTranscriptionEvents.Close, on_close)
                await conn.start(_DG_OPTIONS)
                self._connection = conn
                logger.info("[%s] Deepgram connected (attempt %d)", session_id, attempt + 1)
                break
            except Exception as exc:
                attempt += 1
                delay = _RECONNECT_DELAY_BASE * (2 ** attempt)
                logger.warning(
                    "[%s] Deepgram connect failed (%s), retry in %.1fs", session_id, exc, delay
                )
                await asyncio.sleep(delay)
        else:
            logger.error("[%s] Deepgram: max reconnection attempts reached", session_id)
            return

        # ── Send audio + yield events ─────────────────────────────────────────
        async def _sender():
            try:
                async for chunk in audio_chunks:
                    if chunk:
                        await conn.send(chunk)
                        metrics_registry.increment("audio_bytes_sent", len(chunk))
            except asyncio.CancelledError:
                pass
            finally:
                await conn.finish()

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
        if self._connection:
            try:
                await self._connection.finish()
            except Exception:
                pass
            self._connection = None
