"""
Session Manager – tracks all active WebSocket sessions.
Thread-safe, supports graceful eviction of idle sessions.
"""

import asyncio
import logging
import time
from typing import Dict, Optional

from app.core.config import settings
from app.core.metrics import metrics_registry
from app.models.session import SessionState, TranslatorSession

logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(self) -> None:
        self._sessions: Dict[str, TranslatorSession] = {}
        self._lock = asyncio.Lock()

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    async def create(self, user_id: Optional[str] = None) -> TranslatorSession:
        async with self._lock:
            if len(self._sessions) >= settings.MAX_CONCURRENT_SESSIONS:
                raise RuntimeError("Max concurrent sessions reached")
            session = TranslatorSession(user_id=user_id)
            session.state = SessionState.ACTIVE
            self._sessions[session.session_id] = session
            metrics_registry.session_opened()
            logger.info("Session created: %s (total=%d)", session.session_id, len(self._sessions))
            return session

    async def get(self, session_id: str) -> Optional[TranslatorSession]:
        return self._sessions.get(session_id)

    async def close(self, session_id: str) -> None:
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                session.state = SessionState.CLOSED
                metrics_registry.session_closed()
                logger.info(
                    "Session closed: %s (age=%.1fs, frames=%d)",
                    session_id,
                    session.age_s,
                    session.frames_processed,
                )

    # ── Heartbeat / eviction ─────────────────────────────────────────────────
    async def evict_idle(self) -> None:
        """Remove sessions that have been idle too long. Call periodically."""
        cutoff = settings.SESSION_TIMEOUT_S
        to_remove = [
            sid
            for sid, s in self._sessions.items()
            if s.idle_s > cutoff and s.state != SessionState.CLOSED
        ]
        for sid in to_remove:
            logger.warning("Evicting idle session: %s", sid)
            await self.close(sid)

    @property
    def active_count(self) -> int:
        return len(self._sessions)

    def stats(self) -> dict:
        return {
            "active_sessions": self.active_count,
            "session_ids": list(self._sessions.keys()),
        }


# Singleton
session_manager = SessionManager()
