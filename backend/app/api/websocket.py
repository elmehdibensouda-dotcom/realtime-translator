"""
WebSocket endpoint – heart of the real-time pipeline.

Flow per client:
  1. Client connects  → JWT validated → session created
  2. Client sends raw PCM bytes (16 kHz, mono, s16le)
  3. Backend feeds audio → ASR service (streaming)
  4. On PARTIAL transcript → translate in background → push to client
  5. On FINAL transcript  → confirm translation → push FINAL event
  6. On disconnect → session closed, resources released
"""

import asyncio
import logging
import time
from typing import AsyncGenerator, Optional

from fastapi import WebSocket, WebSocketDisconnect, status

from app.core.metrics import LatencyTimer, metrics_registry
from app.core.security import extract_token_from_query
from app.models.transcript import ErrorEvent, StatusEvent, TranscriptEvent, TranscriptType
from app.services.session_manager import session_manager
from app.services.translation.deepl_service import DeepLTranslationService
from app.services.translation.google_service import GoogleTranslationService
from app.core.config import settings

logger = logging.getLogger(__name__)


def _build_asr():
    if settings.ASR_PROVIDER == "assemblyai" and settings.ASSEMBLYAI_API_KEY:
        from app.services.asr.assemblyai_service import AssemblyAIASRService
        return AssemblyAIASRService()
    if settings.ASR_PROVIDER == "deepgram" and settings.DEEPGRAM_API_KEY:
        from app.services.asr.deepgram_service import DeepgramASRService
        return DeepgramASRService()
    from app.services.asr.google_service import GoogleASRService
    return GoogleASRService()


def _build_translator():
    if settings.TRANSLATION_PROVIDER == "deepl" and settings.DEEPL_API_KEY:
        return DeepLTranslationService()
    return GoogleTranslationService()


async def handle_translation_session(websocket: WebSocket, token: Optional[str]) -> None:
    """Main WebSocket handler – called by the router."""

    # ── Auth ─────────────────────────────────────────────────────────────────
    try:
        claims = extract_token_from_query(token)
        user_id = claims.get("sub", "anonymous")
    except Exception as exc:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=str(exc))
        return

    # ── Accept & session ──────────────────────────────────────────────────────
    await websocket.accept()
    try:
        session = await session_manager.create(user_id=user_id)
    except RuntimeError as exc:
        await websocket.send_text(
            ErrorEvent(code="MAX_SESSIONS", message=str(exc), recoverable=False).model_dump_json()
        )
        await websocket.close()
        return

    sid = session.session_id

    # Notify client of successful connection
    await websocket.send_text(
        StatusEvent(event="connected", session_id=sid, message="Ready to stream").model_dump_json()
    )
    logger.info("[%s] Client connected (user=%s)", sid, user_id)

    # ── Services ──────────────────────────────────────────────────────────────
    asr = _build_asr()
    translator = _build_translator()

    # ── Audio chunk generator (from WebSocket) ────────────────────────────────
    audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=200)

    async def _audio_generator() -> AsyncGenerator[bytes, None]:
        while True:
            chunk = await audio_queue.get()
            if chunk is None:
                break
            yield chunk

    # ── Receiver task (WebSocket → queue) ────────────────────────────────────
    async def _receiver():
        try:
            while True:
                data = await websocket.receive_bytes()
                session.bytes_received += len(data)
                session.frames_processed += 1
                session.touch()
                await audio_queue.put(data)
        except WebSocketDisconnect:
            logger.info("[%s] Client disconnected", sid)
        except Exception as exc:
            logger.warning("[%s] Receiver error: %s", sid, exc)
        finally:
            await audio_queue.put(None)   # sentinel → stop ASR

    # ── Pipeline: ASR → translate → push ─────────────────────────────────────
    async def _pipeline():
        try:
            async for asr_event in asr.transcribe_stream(_audio_generator(), sid):
                # Skip empty transcripts
                if not asr_event.transcript_en.strip():
                    continue

                t_pipeline_start = time.perf_counter()

                # Translate (PARTIAL and FINAL)
                try:
                    with LatencyTimer("translation_latency_ms"):
                        translation = await translator.translate(asr_event.transcript_en)
                except Exception as tex:
                    logger.warning("[%s] Translation error: %s", sid, tex)
                    translation = ""
                    metrics_registry.increment("translation_errors_total")

                total_ms = (time.perf_counter() - t_pipeline_start) * 1000
                metrics_registry.record_latency("pipeline_latency_ms", total_ms)

                # Enrich event
                enriched = TranscriptEvent(
                    type=asr_event.type,
                    session_id=sid,
                    sequence=session.next_seq(),
                    transcript_en=asr_event.transcript_en,
                    confidence=asr_event.confidence,
                    translation_fr=translation,
                    asr_latency_ms=asr_event.asr_latency_ms,
                    translation_latency_ms=round(total_ms, 1),
                    total_latency_ms=round(
                        (asr_event.asr_latency_ms or 0) + total_ms, 1
                    ),
                )

                # Push to client (fire-and-forget if slow)
                try:
                    await asyncio.wait_for(
                        websocket.send_text(enriched.model_dump_json()),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    logger.warning("[%s] Client too slow – frame dropped", sid)
                    metrics_registry.increment("frames_dropped_total")
                except Exception:
                    break  # client gone

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("[%s] Pipeline error: %s", sid, exc, exc_info=True)
            metrics_registry.increment("pipeline_errors_total")

    # ── Run both tasks concurrently ───────────────────────────────────────────
    receiver_task = asyncio.create_task(_receiver())
    pipeline_task = asyncio.create_task(_pipeline())

    try:
        await asyncio.gather(receiver_task, pipeline_task)
    except Exception as exc:
        logger.error("[%s] Session fatal error: %s", sid, exc)
    finally:
        receiver_task.cancel()
        pipeline_task.cancel()
        await asyncio.gather(receiver_task, pipeline_task, return_exceptions=True)
        await asr.close()
        await translator.close()
        await session_manager.close(sid)
        logger.info("[%s] Session fully cleaned up", sid)
