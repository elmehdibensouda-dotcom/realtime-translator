import logging
import time
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect, status

from app.services.translation.free_service import FreeTranslationService
from app.services.session_manager import session_manager

logger = logging.getLogger(__name__)

# Global singleton for hardware/resource reuse
translation_service = FreeTranslationService()


async def handle_translation_session(websocket: WebSocket, token: Optional[str]) -> None:
    """
    Receive text JSON from browser (Web Speech API) → translate → send back.

    Receive: {"text": "hello world", "is_final": true}
    Send:    {"type": "partial"|"final", "transcript_en": "...", "translation_fr": "..."}
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token missing")
        return

    session = await session_manager.create()
    session_id = session.session_id

    try:
        await websocket.accept()
        logger.info("[%s] WebSocket accepted", session_id)

        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                break

            text = (data.get("text") or "").strip()
            is_final = bool(data.get("is_final", False))

            if not text:
                continue

            seq_id = data.get("seq_id")
            translation = await translation_service.translate(text)

            response = {
                "type": "final" if is_final else "partial",
                "transcript_en": text,
                "translation_fr": translation,
            }
            if seq_id:
                response["seq_id"] = seq_id
            
            await websocket.send_json(response)

    except Exception as e:
        logger.error("[%s] Session error: %s", session_id, e)
    finally:
        await session_manager.close(session_id)
        logger.info("[%s] Session closed", session_id)
