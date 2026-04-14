"""Main API router – registers all sub-routers and WebSocket endpoint."""

from typing import Optional
from fastapi import APIRouter, Query, WebSocket
from app.api.auth import router as auth_router
from app.api.websocket import handle_translation_session
from app.services.session_manager import session_manager

api_router = APIRouter()

# REST sub-routers
api_router.include_router(auth_router)


@api_router.websocket("/ws/translate")
async def ws_translate(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None, description="JWT access token"),
):
    """
    WebSocket endpoint for real-time audio → transcript → translation.

    Connect: wss://<host>/ws/translate?token=<jwt>
    Send:    raw PCM bytes (16 kHz, mono, signed 16-bit little-endian)
    Receive: JSON TranscriptEvent | ErrorEvent | StatusEvent
    """
    await handle_translation_session(websocket, token)


@api_router.get("/sessions", tags=["Admin"])
async def list_sessions():
    """Active session stats (admin use only – secure in production)."""
    return session_manager.stats()
